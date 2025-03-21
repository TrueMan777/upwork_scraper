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

- Python 3.8 or higher
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
   UPWORK_USERNAME=your_username
   UPWORK_PASSWORD=your_password

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
   - `description` (Long Text)
   - `client_info` (Long Text)
   - `job_details` (Long Text)
   - `skills` (Long Text)
   - `proposals` (Text)
   - `is_processed` (Boolean, optional)
   - `score` (Number, optional)
4. Generate an API key from your Baserow account settings
5. Add the API key and table ID to your `.env` file

## Basic Usage

### Command Line Interface

The basic syntax for using the scraper is:

```bash
python -m upwork_scraper.main [OPTIONS]
```

### Examples

1. Scrape web scraping jobs (one page):
   ```bash
   python -m upwork_scraper.main --query "web scraping"
   ```

2. Scrape Python developer jobs (multiple pages):
   ```bash
   python -m upwork_scraper.main --query "python developer" --max-pages 3
   ```

3. Using a specific scraper implementation:
   ```bash
   python -m upwork_scraper.main --scraper selenium --query "data mining"
   ```

## Advanced Usage

### Command Line Options

The following options are available:

- `--scraper`: Choose between `crawl4ai` (default) or `selenium` implementations
- `--query`: Search query for jobs (default: "web scraping")
- `--max-pages`: Maximum number of pages to scrape (default: 1)
- `--headless`: Run browser in headless mode (flag, default: True)
- `--no-headless`: Run browser in non-headless mode (opposite of `--headless`)
- `--days-to-keep`: Number of days to keep jobs in Baserow (default: 30)

### Examples

1. Non-headless mode (for debugging):
   ```bash
   python -m upwork_scraper.main --no-headless --query "web development" --max-pages 1
   ```

2. Keep jobs for a longer period:
   ```bash
   python -m upwork_scraper.main --query "machine learning" --days-to-keep 60
   ```

3. Using as a module in your own script:
   ```python
   import asyncio
   from upwork_scraper.scrapers import JobsScraperCrawl4ai

   async def my_custom_scraper():
       scraper = JobsScraperCrawl4ai(
           cookies_file="upwork_cookies_selenium.json",
           output_dir="my_jobs",
           headless=True,
           verbose=True
       )
       
       jobs = await scraper.scrape_jobs(
           query="data science",
           max_pages=2
       )
       
       print(f"Found {len(jobs)} jobs")
       return jobs

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
- `posted_time`: When the job was posted
- `description`: Job description text
- `client_info`: Information about the client (payment verification, rating, etc.)
- `job_details`: Details like job type, budget, and duration
- `skills`: Required skills for the job
- `proposals`: Number of proposals submitted

### Output Files

Jobs are saved to the specified output directory (default: `jobs/`) in JSON format. Each file is named with a timestamp for easy tracking.

Example:
```
jobs/extracted_jobs_20230321_120000.json
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**:
   - Ensure your Upwork credentials are correct
   - Check if you need to solve a CAPTCHA by running in non-headless mode
   - Try manually logging in with a browser and exporting cookies

2. **Scraping Errors**:
   - Upwork might block automated access; try reducing scraping frequency
   - Ensure your internet connection is stable
   - Check if Upwork's website structure has changed

3. **Baserow Integration Issues**:
   - Verify your API key and table ID
   - Ensure your table structure matches the expected fields
   - Check Baserow's API status

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