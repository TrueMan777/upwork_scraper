"""
Test script for the BaserowService class.

This script tests basic functionality of the BaserowService class.
You need to have BASEROW_API_KEY and BASEROW_TABLE_ID environment variables set.
"""

import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
# Import the BaserowService from the local module
from .baserow import BaserowService

# Load environment variables
load_dotenv()


async def test_baserow_service():
    """Test the basic functionality of the BaserowService class."""
    # Create an instance of the BaserowService
    service = BaserowService()

    print("Testing BaserowService...")
    print(f"Using table ID: {service.table_id}")

    # 1. Get all rows
    print("\n1. Getting all rows...")
    rows = await service.get_all_rows()
    print(f"Found {len(rows)} rows")

    if len(rows) > 0:
        # Print the first row
        print("First row:")
        print(json.dumps(rows[0], indent=2))

    # 2. Create a test row
    print("\n2. Creating a test row...")
    test_job = {
        "job_uid": f"test-job-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "job_title": "Test Job from BaserowService",
        "job_url": "https://upwork.com/test",
        "posted_time": "just now",
        "description": "This is a test job created by the BaserowService test script",
        "client_info": {"location": "Test Country", "rating": "5.0"},
        "job_details": {"budget": "$100-$500", "duration": "Less than 1 month"},
        "skills": ["Python", "Web Scraping", "API Integration"],
        "proposals": "Less than 5",
    }

    created_row = await service.add_row(test_job)
    if created_row:
        print("Test row created successfully!")
        print(f"Row ID: {created_row.get('id')}")
        row_id = created_row.get('id')

        # 3. Get the created row
        print("\n3. Getting the created row...")
        retrieved_row = await service.get_row(row_id)
        if retrieved_row:
            print("Row retrieved successfully!")
            print(f"Job title: {retrieved_row.get('job_title')}")

        # 4. Update the row
        print("\n4. Updating the row...")
        update_data = {
            "job_title": "Updated Test Job",
            "description": "This job was updated by the test script"
        }
        updated_row = await service.update_row(row_id, update_data)
        if updated_row:
            print("Row updated successfully!")
            print(f"New job title: {updated_row.get('job_title')}")

        # 5. Delete the test row
        print("\n5. Deleting the test row...")
        if await service.delete_row(row_id):
            print("Row deleted successfully!")
    else:
        print("Failed to create test row!")

    # 6. Test bulk upload with deduplication
    print("\n6. Testing bulk upload with deduplication...")
    test_jobs = [
        {
            "job_uid": "test-bulk-1",
            "job_title": "Bulk Test Job 1",
            "job_url": "https://upwork.com/test1",
            "posted_time": "1 hour ago",
            "description": "This is a bulk test job 1",
            "client_info": {"location": "Test Country 1"},
            "job_details": {"budget": "$100"},
            "skills": ["Python", "Data Analysis"],
            "proposals": "10+",
        },
        {
            "job_uid": "test-bulk-2",
            "job_title": "Bulk Test Job 2",
            "job_url": "https://upwork.com/test2",
            "posted_time": "2 hours ago",
            "description": "This is a bulk test job 2",
            "client_info": {"location": "Test Country 2"},
            "job_details": {"budget": "$200"},
            "skills": ["JavaScript", "React"],
            "proposals": "5-10",
        },
    ]

    created_bulk_rows = await service.upload_multiple_rows(test_jobs)
    print(f"Created {len(created_bulk_rows)} bulk rows")

    # Get the IDs of the created rows
    bulk_row_ids = [row.get('id') for row in created_bulk_rows]

    # Test deduplication by trying to upload the same rows again
    print("\n7. Testing deduplication...")
    duplicated_rows = await service.upload_multiple_rows(test_jobs)
    print(f"Created {len(duplicated_rows)} rows after deduplication (should be 0)")

    # Clean up the bulk test rows
    print("\n8. Cleaning up bulk test rows...")
    for row_id in bulk_row_ids:
        if await service.delete_row(row_id):
            print(f"Deleted row {row_id}")

    print("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(test_baserow_service()) 