"""
Baserow Service for handling all interactions with the Baserow API.

This module provides a service class for interacting with Baserow,
encapsulating all Baserow operations including getting, creating,
updating, and deleting rows with proper error handling and retries.
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s ||| <%(name)s>",
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
        """Get all rows from the specified table, handling pagination.

        Args:
            table_id: The Baserow table ID. If None, uses the instance's table ID.
            filters: Optional filters to apply to the query.

        Returns:
            A list of dictionaries, each representing a row in the table.
        """
        url = self._get_url(table_id)
        headers = self._get_headers()
        all_rows = []
        page = 1
        size = 100  # Baserow default page size

        try:
            while True:
                # Add pagination parameters to filters
                page_filters = filters.copy() if filters else {}
                page_filters.update({
                    'page': page,
                    'size': size
                })

                response = await self._request_with_retry("GET", url, headers, params=page_filters)
                data = response.json()

                results = data.get('results', [])
                if not results:
                    break

                all_rows.extend(results)

                # Check if there are more pages
                if not data.get('next'):
                    break

                page += 1
                # Add a small delay to prevent rate limiting
                await asyncio.sleep(0.5)

            logger.info(f"Retrieved {len(all_rows)} rows in total")
            return all_rows

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
                    is_duplicate = False
                    for existing_row in existing_rows:
                        try:
                            existing_value = int(existing_row.get(deduplication_field, 0))
                            new_value = int(row.get(deduplication_field, 0))
                            if existing_value == new_value:
                                logger.info(f"Skipping duplicate row with {deduplication_field}: {new_value}")
                                is_duplicate = True
                                break
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Error comparing {deduplication_field} values: {e}")
                            # Fall back to string comparison
                            if str(existing_row.get(deduplication_field)) == str(row.get(deduplication_field)):
                                logger.info(f"Skipping duplicate row (string comparison) with {deduplication_field}: {row.get(deduplication_field)}")
                                is_duplicate = True
                                break

                    if is_duplicate:
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

    async def find_duplicates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Find duplicate jobs in the database based on job_uid.

        This method retrieves all rows and groups them by job_uid to identify duplicates.
        A job is considered a duplicate if its job_uid appears more than once.

        Returns:
            A dictionary where:
            - key: job_uid that has duplicates
            - value: list of duplicate row data for that job_uid
        """
        try:
            # Get all rows from the database
            all_rows = await self.get_all_rows()

            # Group rows by job_uid
            job_uid_groups: Dict[str, List[Dict[str, Any]]] = {}
            for row in all_rows:
                job_uid = str(row.get('job_uid', ''))  # Convert to string for consistency
                if not job_uid:
                    continue

                if job_uid in job_uid_groups:
                    job_uid_groups[job_uid].append(row)
                else:
                    job_uid_groups[job_uid] = [row]

            # Filter for only the groups that have duplicates
            duplicates = {
                job_uid: rows
                for job_uid, rows in job_uid_groups.items()
                if len(rows) > 1
            }

            if duplicates:
                logger.info(f"Found {len(duplicates)} job_uids with duplicates")
                for job_uid, rows in duplicates.items():
                    logger.info(f"job_uid {job_uid} has {len(rows)} duplicate entries")
            else:
                logger.info("No duplicates found")

            return duplicates

        except Exception as e:
            logger.error(f"Error finding duplicates: {str(e)}")
            return {}

    async def find_similar_jobs(self, update_status: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """Find jobs that have the same title, location, and skills.

        This method retrieves all rows and groups them by a composite key of
        title + location + skills to identify similar jobs that might be duplicates
        even if they have different job_uids.

        Returns:
            A dictionary where:
            - key: A composite key of title + location + skills
            - value: list of similar job entries
        """
        try:
            # Get all rows from the database
            all_rows = await self.get_all_rows()

            # Group rows by composite key
            similar_groups: Dict[str, List[Dict[str, Any]]] = {}

            for row in all_rows:
                # Get the relevant fields
                title = str(row.get('job_title', '')).strip().lower()
                location = str(row.get('location', '')).strip().lower()
                skills = str(row.get('skills', '[]')).strip().lower()  # Skills are stored as string

                if not title:  # Skip rows without a title
                    continue

                # Create a composite key
                composite_key = f"{title}|{location}|{skills}"

                if composite_key in similar_groups:
                    similar_groups[composite_key].append(row)
                else:
                    similar_groups[composite_key] = [row]

            # Filter for only the groups that have duplicates
            similar_jobs = {
                key: rows
                for key, rows in similar_groups.items()
                if len(rows) > 1
            }

            if similar_jobs:
                logger.info(f"Found {len(similar_jobs)} groups of similar jobs:")
                for key, rows in similar_jobs.items():
                    title = rows[0].get('job_title', 'N/A')
                    location = rows[0].get('location', 'N/A')
                    logger.info(
                        f"\nSimilar jobs found:"
                        f"\n  Title: {title}"
                        f"\n  Location: {location}"
                        f"\n  Count: {len(rows)}"
                    )
                    if update_status:
                        for row in rows:
                            await self.update_row(row.get('id'), {'status': 'duplicate'})
            else:
                logger.info("No similar jobs found")

            return similar_jobs

        except Exception as e:
            logger.error(f"Error finding similar jobs: {str(e)}")
            return {}

    async def delete_duplicates(self, keep_newest: bool = True) -> int:
        """Delete duplicate jobs, keeping either the newest or oldest entry.

        Args:
            keep_newest: If True, keeps the newest entry for each duplicate set.
                       If False, keeps the oldest entry.

        Returns:
            Number of rows deleted.
        """
        try:
            duplicates = await self.find_duplicates()
            if not duplicates:
                return 0

            deleted_count = 0
            for job_uid, rows in duplicates.items():
                # Sort rows by posted_time_date if available, otherwise by ID
                sorted_rows = sorted(
                    rows,
                    key=lambda x: (
                        x.get('posted_time_date', ''),
                        x.get('id', 0)
                    ),
                    reverse=keep_newest
                )

                # Keep the first row (newest or oldest based on keep_newest)
                rows_to_delete = sorted_rows[1:]

                # Delete duplicate rows
                for row in rows_to_delete:
                    row_id = row.get('id')
                    if row_id:
                        success = await self.delete_row(str(row_id))
                        if success:
                            deleted_count += 1
                            logger.info(f"Deleted duplicate row {row_id} for job_uid {job_uid}")
                        else:
                            logger.warning(f"Failed to delete duplicate row {row_id} for job_uid {job_uid}")

            logger.info(f"Deleted {deleted_count} duplicate rows")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting duplicates: {str(e)}")
            return 0
