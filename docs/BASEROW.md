# Baserow Integration Guide

This guide explains how to set up and use [Baserow](https://baserow.io/) as a data storage solution for the Upwork Scraper.

## Table of Contents

- [What is Baserow?](#what-is-baserow)
- [Setup Instructions](#setup-instructions)
- [Table Configuration](#table-configuration)
- [API Key Generation](#api-key-generation)
- [Integration with Upwork Scraper](#integration-with-upwork-scraper)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)

## What is Baserow?

Baserow is an open-source no-code database tool and Airtable alternative. It provides an intuitive interface for creating and managing databases without requiring SQL knowledge. For the Upwork Scraper, Baserow serves as:

1. A persistent storage solution for scraped job data
2. A convenient way to view, filter, and analyze job listings
3. A platform for additional automation and integrations

## Setup Instructions

### 1. Create a Baserow Account

First, create a free account at [baserow.io](https://baserow.io/). You can use:

- The cloud-hosted version (free tier available)
- Self-hosted version (if you prefer to host it yourself)

### 2. Create a New Database

After logging in:

1. Click "Create database"
2. Name it (e.g., "Upwork Jobs")
3. Create a new table named "Jobs"

## Table Configuration

Configure your "Jobs" table with the following fields:

| Field Name     | Field Type    | Description                                 |
|----------------|---------------|---------------------------------------------|
| job_uid        | Text          | Unique identifier for the job               |
| job_title      | Text          | Title of the job posting                    |
| job_url        | URL           | Direct link to the job posting              |
| posted_time    | Text          | When the job was posted                     |
| description    | Long text     | Full job description                        |
| client_info    | Long text     | JSON string with client information         |
| job_details    | Long text     | JSON string with job details                |
| skills         | Long text     | JSON array of required skills               |
| proposals      | Text          | Number of proposals submitted               |
| score          | Number        | Job relevance score (optional)              |

You can add additional fields as needed for your specific use case.

## API Key Generation

To allow the Upwork Scraper to interact with your Baserow database:

1. Click on your user avatar in the top-right corner
2. Select "Account"
3. Go to the "API tokens" section
4. Click "Create new token"
5. Provide a name (e.g., "Upwork Scraper")
6. Set appropriate permissions (at minimum: "Read database" and "Create rows")
7. Copy the generated token

## Integration with Upwork Scraper

### 1. Find Your Table ID

To find your table ID:

1. Navigate to your table in Baserow
2. Look at the URL, which should look like: `https://baserow.io/database/123/table/456`
3. The number after `table/` is your table ID (in this example, `456`)

### 2. Configure Environment Variables

Add these variables to your `.env` file:

```
BASEROW_API_KEY=your_api_key_here
BASEROW_TABLE_ID=your_table_id_here
```

## Common Operations

The Upwork Scraper integrates with Baserow through the `BaserowService` class, which provides several useful methods:

### Getting All Rows

```python
from upwork_scraper.data.baserow import BaserowService

async def get_all_jobs():
    baserow = BaserowService()
    rows = await baserow.get_all_rows()
    return rows
```

### Uploading New Jobs

```python
async def upload_jobs(jobs):
    baserow = BaserowService()
    created_rows = await baserow.upload_multiple_rows(
        jobs,
        deduplicate=True,
        deduplication_field="job_uid"
    )
    return created_rows
```

### Cleaning Up Old Jobs

```python
async def cleanup_old_jobs(days=30):
    baserow = BaserowService()
    deleted_count = await baserow.clean_up_old_rows(days=days)
    return deleted_count
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify your API key is correctly copied
   - Check if the API token has expired
   - Ensure the token has appropriate permissions

2. **Table Configuration Issues**:
   - Confirm all required fields exist and have correct names
   - Check field types match the expected formats
   - Ensure the table ID is correct

3. **Rate Limiting**:
   - Baserow may have rate limits depending on your plan
   - Add appropriate delays between requests if necessary

### Debugging Tips

When troubleshooting Baserow integration issues:

1. Check the response status and body from Baserow API calls
2. Verify the data format being sent matches Baserow expectations
3. Try manual API requests using tools like curl or Postman

### API Documentation

For more advanced usage, refer to the [Baserow API documentation](https://baserow.io/api-docs).