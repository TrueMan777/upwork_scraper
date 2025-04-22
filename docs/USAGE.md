# Upwork Scraper Usage Guide

This document provides detailed instructions on how to use the Upwork Scraper tool effectively.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Basic Usage](#basic-usage)
- [Advanced Usage](#advanced-usage)
- [Understanding Output](#understanding-output)
- [Troubleshooting](#troubleshooting)

## Installation

### Prerequisites

- Python 3.12 or higher
- pip (Python package installer)
- Git (optional, for cloning the repository)

### Steps

1. Clone the repository (or download and extract the ZIP file):
   ```bash
   git clone https://github.com/yourusername/upwork-scraper.git
   cd upwork-scraper
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Install the package in development mode (optional):
   ```bash
   pip install -e .
   ```

## Configuration

The Upwork Scraper requires certain configuration settings to operate correctly. These can be provided through environment variables or a `.env` file.

1. Create a `.env` file in the project root directory based on the `.env.example` template:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your specific values:
   ```
   # Upwork credentials
   UPWORK_EMAIL=your_email
   UPWORK_PASSWORD=your_password
   UPWORK_SECURITY_ANSWER=your_security_answer  # Optional, if your account uses security questions

   # Baserow configuration
   BASEROW_API_KEY=your_baserow_api_key
   BASEROW_TABLE_ID=your_baserow_table_id
   ```

### Baserow Setup

To use the Baserow integration:

1. Create an account at [Baserow](https://baserow.io/)
2. Create a new database and table
3. Configure the table with the following fields:
   - `job_uid` (Text)
   - `job_title` (Text)
   - `job_url` (URL)
   - `posted_time` (Text)
   - `posted_time_date` (Date/Time)
   - `description` (Long Text)
   - `location` (Text)
   - `rating` (Number)
   - `total_feedback` (Text)
   - `spent` (Text)
   - `budget` (Text)
   - `job_type` (Text)
   - `client_info` (Long Text)
   - `job_details` (Long Text)
   - `skills` (Long Text)
   - `proposals` (Text)
   - `status` (Text)
4. Generate an API key from your Baserow account settings
5. Add the API key and table ID to your `.env` file

## Basic Usage

### Command Line Interface

The basic syntax for using the scraper is:

```bash
python -m upwork_scraper.main [OPTIONS]
```

### Examples

1. Use default queries (recommended):
   ```bash
   python -m upwork_scraper.main
   ```

2. Specify custom search queries:
   ```bash
   python -m upwork_scraper.main --queries "web scraping" "python developer" "data mining"
   ```

3. Using a specific scraper implementation:
   ```bash
   python -m upwork_scraper.main --scraper selenium --queries "data mining"
   ```

## Advanced Usage

### Command Line Options

The following options are available:

- `--scraper`: Choose between `selenium` (default) or `crawl4ai` implementations
- `--queries`: One or more search queries for jobs (default: predefined list of relevant queries)
- `--max-pages`: Maximum number of pages to scrape per query (default: 2)
- `--headless`: Run browser in headless mode (flag, default: False)
- `--no-headless`: Run browser in non-headless mode (default behavior)
- `--days-to-keep`: Number of days to keep jobs in Baserow (default: 365)

### Default Search Queries

The scraper comes with a predefined list of relevant queries:
```python
DEFAULT_QUERIES = [
    "web scraping",
    "data scraping",
    "scraping",
    "ai development",
    "elevenlabs",
    "scraping",
    "ai automation",
    "n8n",
    "angularjs",
    "angular"
]
```

### Examples

1. Non-headless mode (default):
   ```bash
   python -m upwork_scraper.main --queries "web development" --max-pages 3
   ```

2. Headless mode with custom retention period:
   ```bash
   python -m upwork_scraper.main --headless --days-to-keep 180
   ```

3. Using as a module in your own script:
   ```python
   import asyncio
   from upwork_scraper.scrapers import JobsScraperSelenium
   from upwork_scraper.data.baserow import BaserowService

   async def my_custom_scraper():
       # Initialize scraper
       scraper = JobsScraperSelenium(
           cookies_file="upwork_cookies_selenium.json",
           output_dir="my_jobs",
           headless=False,
           verbose=True
       )

       # Scrape jobs
       jobs = await scraper.scrape_jobs(
           query="data science",
           max_pages=2
       )

       # Upload to Baserow
       if jobs:
           baserow = BaserowService()
           created_rows = await baserow.upload_multiple_rows(
               jobs,
               deduplicate=True,
               deduplication_field="job_uid"
           )
           print(f"Uploaded {len(created_rows)} new jobs to Baserow")

   # Run the async function
   if __name__ == "__main__":
       asyncio.run(my_custom_scraper())
   ```

## Understanding Output

### Job Data Format

Each scraped job contains the following information:

- `job_uid`: Unique identifier for the job
- `job_title`: Title of the job posting
- `job_url`: URL to the job posting
- `posted_time`: When the job was posted (relative time)
- `posted_time_date`: Parsed UTC datetime of posting
- `description`: Job description text
- `location`: Client's location
- `rating`: Client's rating (with 2 decimal points)
- `total_feedback`: Number of client reviews
- `spent`: Amount spent by client
- `budget`: Job budget
- `job_type`: Type of job (hourly/fixed)
- `client_info`: Full client information as JSON string
- `job_details`: Job details as JSON string
- `skills`: Required skills as JSON array
- `proposals`: Number of proposals submitted
- `status`: Job status (scraped/low_rating)

### Status Values

- `scraped`: Default status for newly scraped jobs
- `low_rating`: Applied to jobs where client rating is < 4.0


### Output Files
Jobs are saved to the specified output directory (default: `jobs/`) in JSON format. Each file is named with a timestamp
for easy tracking.

Example:
```
jobs/extracted_jobs_20230321_120000.json
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Ensure your Upwork credentials are correct
   - Check if you need to provide a security answer in `.env`
   - Try running in non-headless mode to see the login process

2. **Scraping Errors**:
   - Upwork might block automated access; try reducing scraping frequency
   - Ensure your internet connection is stable
   - Check if Upwork's website structure has changed

3. **Baserow Integration Issues**:
   - Verify your API key and table ID
   - Ensure your table structure matches the expected fields
   - Check Baserow's API status and rate limits

### Debugging

For more verbose logging, set the `LOG_LEVEL` environment variable to `DEBUG`:

```bash
LOG_LEVEL=DEBUG python -m upwork_scraper.main
```

Or modify your `.env` file:
```
LOG_LEVEL=DEBUG
```

### Support

If you encounter issues not covered here, please open an issue on the GitHub repository with:
- A description of the problem
- Steps to reproduce
- Relevant logs (with sensitive information redacted)
- Your environment details (OS, Python version, etc.)