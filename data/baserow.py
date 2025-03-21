"""
Baserow Service for handling all interactions with the Baserow API.

This module provides a service class for interacting with Baserow,
encapsulating all Baserow operations including getting, creating,
updating, and deleting rows with proper error handling and retries.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Import helpers from utils
from utils.helpers import load_json_file, save_json_file, is_file_older_than

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class BaserowService:
    """Service for interacting with the Baserow API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        table_id: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize the BaserowService.

        Args:
            api_key: The Baserow API key. If None, reads from environment variable.
            table_id: The Baserow table ID. If None, reads from environment variable.
            base_url: The Baserow API base URL. If None, uses default.
            max_retries: Maximum number of retries for failed requests.
            retry_delay: Delay between retries in seconds.
        """
        self.api_key = api_key or os.getenv("BASEROW_API_KEY")
        if not self.api_key:
            raise ValueError("Baserow API key not provided and not found in environment")

        self.table_id = table_id or os.getenv("BASEROW_TABLE_ID")
        if not self.table_id:
            raise ValueError("Baserow table ID not provided and not found in environment")

        self.base_url = base_url or "https://api.baserow.io/api/database/rows/table"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.info("BaserowService initialized")

    def _get_headers(self) -> Dict[str, str]:
        """Get the headers for Baserow API requests.

        Returns:
            A dictionary of headers for Baserow API requests.
        """
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def _get_url(self, table_id: Optional[str] = None, row_id: Optional[str] = None) -> str:
        """Get the URL for Baserow API requests.

        Args:
            table_id: The table ID. If None, uses the instance's table ID.
            row_id: The row ID. If provided, includes it in the URL.

        Returns:
            The URL for the Baserow API request.
        """
        table_id = table_id or self.table_id
        base_url = f"{self.base_url}/{table_id}/?user_field_names=true"

        if row_id:
            return f"{self.base_url}/{table_id}/{row_id}/?user_field_names=true"

        return base_url

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """Make an HTTP request with retry logic.

        Args:
            method: The HTTP method (GET, POST, PATCH, DELETE).
            url: The URL for the request.
            headers: The headers for the request.
            json_data: The JSON data for the request (for POST/PATCH).
            params: The query parameters for the request.

        Returns:
            The Response object from the requests library.

        Raises:
            Exception: If all retry attempts fail.
        """
        attempts = 0
        last_exception = None

        while attempts < self.max_retries:
            try:
                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=params)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, json=json_data)
                elif method.upper() == "PATCH":
                    response = requests.patch(url, headers=headers, json=json_data)
                elif method.upper() == "DELETE":
                    response = requests.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response

            except Exception as e:
                attempts += 1
                last_exception = e
                logger.warning(
                    f"Request failed (attempt {attempts}/{self.max_retries}): {str(e)}"
                )

                if attempts < self.max_retries:
                    # Exponential backoff with jitter
                    delay = self.retry_delay * (2 ** (attempts - 1))
                    await asyncio.sleep(delay)

        logger.error(f"All retry attempts failed: {str(last_exception)}")
        raise last_exception

    async def get_all_rows(
        self,
        table_id: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get all rows from the specified table.

        Args:
            table_id: The Baserow table ID. If None, uses the instance's table ID.
            filters: Optional filters to apply to the query.

        Returns:
            A list of dictionaries, each representing a row in the table.
        """
        url = self._get_url(table_id)
        headers = self._get_headers()

        try:
            response = await self._request_with_retry("GET", url, headers, params=filters)
            return response.json()["results"]
        except Exception as e:
            logger.error(f"Error getting rows: {str(e)}")
            return []

    async def get_row(
        self,
        row_id: str,
        table_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a row by ID.

        Args:
            row_id: The ID of the row to get.
            table_id: The Baserow table ID. If None, uses the instance's table ID.

        Returns:
            The row data as a dictionary, or None if the row was not found.
        """
        url = self._get_url(table_id, row_id)
        headers = self._get_headers()

        try:
            response = await self._request_with_retry("GET", url, headers)
            return response.json()
        except Exception as e:
            logger.error(f"Error getting row {row_id}: {str(e)}")
            return None

    async def add_row(
        self,
        data: Dict[str, Any],
        table_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Add a row to the specified table.

        Args:
            data: The data for the new row.
            table_id: The Baserow table ID. If None, uses the instance's table ID.

        Returns:
            The created row data as returned by Baserow, or None if creation failed.
        """
        url = self._get_url(table_id)
        headers = self._get_headers()

        try:
            response = await self._request_with_retry("POST", url, headers, json_data=data)
            logger.info(f"Row added successfully: {data.get('job_title', 'No title')}")
            return response.json()
        except Exception as e:
            logger.error(f"Error adding row: {str(e)}")
            return None

    async def update_row(
        self,
        row_id: str,
        data: Dict[str, Any],
        table_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a row in the specified table.

        Args:
            row_id: The ID of the row to update.
            data: The data to update in the row.
            table_id: The Baserow table ID. If None, uses the instance's table ID.

        Returns:
            The updated row data as returned by Baserow, or None if update failed.
        """
        url = self._get_url(table_id, row_id)
        headers = self._get_headers()

        try:
            response = await self._request_with_retry("PATCH", url, headers, json_data=data)
            logger.info(f"Row {row_id} updated successfully")
            return response.json()
        except Exception as e:
            logger.error(f"Error updating row {row_id}: {str(e)}")
            return None

    async def delete_row(
        self,
        row_id: str,
        table_id: Optional[str] = None
    ) -> bool:
        """Delete a row from the specified table.

        Args:
            row_id: The ID of the row to delete.
            table_id: The Baserow table ID. If None, uses the instance's table ID.

        Returns:
            True if deletion was successful, False otherwise.
        """
        url = self._get_url(table_id, row_id)
        headers = self._get_headers()

        try:
            await self._request_with_retry("DELETE", url, headers)
            logger.info(f"Row {row_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting row {row_id}: {str(e)}")
            return False

    async def upload_multiple_rows(
        self,
        rows: List[Dict[str, Any]],
        table_id: Optional[str] = None,
        deduplicate: bool = True,
        deduplication_field: str = "job_uid"
    ) -> List[Dict[str, Any]]:
        """Upload multiple rows with deduplication.

        Args:
            rows: The rows to upload.
            table_id: The Baserow table ID. If None, uses the instance's table ID.
            deduplicate: Whether to deduplicate rows based on a field.
            deduplication_field: The field to use for deduplication.

        Returns:
            A list of the created row data as returned by Baserow.
        """
        table_id = table_id or self.table_id
        created_rows = []

        if not rows:
            logger.warning("No rows to upload")
            return created_rows

        # Get existing rows for deduplication if needed
        existing_rows = []
        if deduplicate:
            try:
                existing_rows = await self.get_all_rows(table_id)
                logger.info(f"Found {len(existing_rows)} existing rows for deduplication check")
            except Exception as e:
                logger.error(f"Error getting existing rows for deduplication: {str(e)}")

        # Process each row
        for row in rows:
            try:
                # Check for duplicates if needed
                if deduplicate and existing_rows:
                    if any(existing_row.get(deduplication_field) == row.get(deduplication_field)
                          for existing_row in existing_rows):
                        logger.info(f"Skipping duplicate row: {row.get('job_title', 'No title')}")
                        continue

                # Handle nested data (convert to string)
                processed_row = {}
                for key, value in row.items():
                    if isinstance(value, (dict, list)):
                        processed_row[key] = str(value)
                    else:
                        processed_row[key] = value

                # Add the row
                created_row = await self.add_row(processed_row, table_id)
                if created_row:
                    created_rows.append(created_row)
                    # Add a small delay to prevent rate limiting
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error processing row {row.get('job_title', 'No title')}: {str(e)}")

        logger.info(f"Successfully uploaded {len(created_rows)} rows")
        return created_rows

    async def clean_up_old_rows(
        self,
        days: int = 30,
        table_id: Optional[str] = None,
        date_field: str = "created_on",
    ) -> int:
        """Delete rows older than specified days.

        Args:
            days: Number of days to keep rows for.
            table_id: The Baserow table ID. If None, uses the instance's table ID.
            date_field: The field to use for date comparison.

        Returns:
            The number of rows deleted.
        """
        table_id = table_id or self.table_id
        deleted_count = 0

        # Get all rows
        try:
            rows = await self.get_all_rows(table_id)
            logger.info(f"Found {len(rows)} rows to check for cleanup")

            # Get the cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)

            # Process each row
            for row in rows:
                try:
                    # Parse the date from the row
                    row_date_str = row.get(date_field)
                    if not row_date_str:
                        continue

                    # Try to parse the date
                    try:
                        row_date = datetime.fromisoformat(row_date_str.replace('Z', '+00:00'))
                    except ValueError:
                        # If we can't parse the date, skip this row
                        logger.warning(f"Could not parse date {row_date_str} for row {row.get('id')}")
                        continue

                    # Delete if older than cutoff
                    if row_date < cutoff_date:
                        success = await self.delete_row(row.get('id'), table_id)
                        if success:
                            deleted_count += 1
                            # Add a small delay to prevent rate limiting
                            await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Error processing row {row.get('id')} for cleanup: {str(e)}")

            logger.info(f"Cleaned up {deleted_count} old rows")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up old rows: {str(e)}")
            return 0
