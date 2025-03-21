"""
Main entry point for the Upwork Scraper application.

This script coordinates the authentication, scraping, and data storage components.
"""

import os
import sys
import asyncio
import logging
import argparse
from dotenv import load_dotenv

# Add the parent directory to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from upwork_scraper.auth.login import UpworkAuthenticator
from upwork_scraper.scrapers import JobsScraperCrawl4ai, JobsScraperSelenium
from upwork_scraper.data.baserow import BaserowService
from upwork_scraper.utils.helpers import setup_logging


# Set up logging
logger = setup_logging(log_level="INFO")

# Load environment variables
load_dotenv()

# Constants
COOKIES_FILE = "upwork_cookies_selenium.json"
OUTPUT_DIR = "jobs"
DEFAULT_QUERY = "web scraping"
DEFAULT_MAX_PAGES = 1
DEFAULT_DAYS_TO_KEEP = 30


async def process_jobs_for_baserow(jobs):
    """Process job data for Baserow storage.

    Args:
        jobs: List of job data dictionaries.

    Returns:
        List of processed job dictionaries.
    """
    processed_jobs = []
    for job in jobs:
        processed_job = {
            "job_uid": job["job_uid"],
            "job_title": job["job_title"],
            "job_url": job["job_url"],
            "posted_time": job["posted_time"],
            "description": job.get("description", ""),
            "client_info": str(job.get("client_info", {})),
            "job_details": str(job.get("job_details", {})),
            "skills": str(job.get("skills", [])),
            "proposals": job.get("proposals", ""),
        }
        processed_jobs.append(processed_job)

    return processed_jobs


def parse_arguments():
    """Parse command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Upwork Scraper")

    parser.add_argument(
        "--scraper",
        type=str,
        choices=["crawl4ai", "selenium"],
        default="crawl4ai",
        help="Scraper implementation to use (crawl4ai or selenium)"
    )

    parser.add_argument(
        "--query",
        type=str,
        default=DEFAULT_QUERY,
        help=f"Search query for jobs (default: {DEFAULT_QUERY})"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Maximum number of pages to scrape (default: {DEFAULT_MAX_PAGES})"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )

    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser in non-headless mode"
    )

    parser.add_argument(
        "--days-to-keep",
        type=int,
        default=DEFAULT_DAYS_TO_KEEP,
        help=f"Number of days to keep jobs in Baserow (default: {DEFAULT_DAYS_TO_KEEP})"
    )

    return parser.parse_args()


async def main():
    """Main function that orchestrates the scraping process."""
    # Parse command line arguments
    args = parse_arguments()

    logger.info("Starting Upwork Scraper")
    logger.info(f"Using {args.scraper} scraper")
    logger.info(f"Search query: {args.query}")
    logger.info(f"Max pages: {args.max_pages}")
    logger.info(f"Headless mode: {args.headless}")

    try:
        # Initialize authenticator and perform conditional login
        logger.info("Initializing authenticator")
        authenticator = UpworkAuthenticator()
        login_performed = await authenticator.login_if_needed()

        if login_performed:
            logger.info("Login was performed because cookies were invalid or expired")
        else:
            logger.info("Using existing valid cookies")

        cookies = authenticator.get_cookies()
        logger.info(f"Using {len(cookies)} cookies for requests")

        # Initialize Baserow service
        logger.info("Initializing Baserow service")
        baserow_service = BaserowService()

        # Fetch existing rows from Baserow
        rows = await baserow_service.get_all_rows()
        logger.info(f"Found {len(rows)} existing rows in Baserow")

        # Initialize job scraper based on the selected implementation
        logger.info(f"Initializing {args.scraper} job scraper")

        if args.scraper == "crawl4ai":
            scraper = JobsScraperCrawl4ai(
                cookies_file=COOKIES_FILE,
                output_dir=OUTPUT_DIR,
                headless=args.headless,
                verbose=True
            )
        else:  # selenium
            scraper = JobsScraperSelenium(
                cookies_file=COOKIES_FILE,
                output_dir=OUTPUT_DIR,
                headless=args.headless,
                verbose=True
            )

        # Scrape jobs
        logger.info(f"Scraping {args.max_pages} page(s) of jobs")
        jobs = await scraper.scrape_jobs(
            query=args.query,
            max_pages=args.max_pages
        )

        if not jobs:
            logger.warning("No jobs found during scraping")
        else:
            logger.info(f"Successfully scraped {len(jobs)} jobs")

            # Process and upload jobs to Baserow
            processed_jobs = await process_jobs_for_baserow(jobs)
            created_rows = await baserow_service.upload_multiple_rows(
                processed_jobs,
                deduplicate=True,
                deduplication_field="job_uid"
            )

            logger.info(f"Successfully uploaded {len(created_rows)} new jobs to Baserow")

            # Clean up old rows
            deleted_count = await baserow_service.clean_up_old_rows(days=args.days_to_keep)
            logger.info(f"Cleaned up {deleted_count} old rows from Baserow")

        logger.info("Upwork Scraper completed successfully")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)