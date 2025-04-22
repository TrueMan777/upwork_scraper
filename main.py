"""
Main entry point for the Upwork Scraper application.

This script coordinates the authentication, scraping, and data storage components.
"""

import os
import sys
import asyncio
import logging
import argparse
import warnings
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pytz
from typing import List
# Add the parent directory to sys.path to enable absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from upwork_scraper.auth.login import UpworkAuthenticator
from upwork_scraper.scrapers import JobsScraperCrawl4ai, JobsScraperSelenium
from upwork_scraper.data.baserow import BaserowService
from upwork_scraper.utils.helpers import setup_logging, parse_relative_time

# Filter out specific selenium_driverless warning
warnings.filterwarnings("ignore", message="got execution_context_id and unique_context=True*")

# Set up logging
logger = setup_logging(log_level="INFO")

# Load environment variables
load_dotenv()

# Constants
COOKIES_FILE = "upwork_cookies_selenium.json"
OUTPUT_DIR = "jobs"
DEFAULT_QUERIES = ["web scraping", "data scraping", "scraping", "ai development", "elevenlabs", "scraping", "ai automation", "n8n", "angularjs", "angular"]  # List of default queries
DEFAULT_MAX_PAGES = 2
DEFAULT_DAYS_TO_KEEP = 365


async def process_jobs_for_baserow(jobs):
    """Process job data for Baserow storage.

    Args:
        jobs: List of job data dictionaries.

    Returns:
        List of processed job dictionaries.
    """
    processed_jobs = []
    for job in jobs:
        # Parse the relative time string into a UTC datetime object
        posted_time_str = job["posted_time"]
        posted_time, success = parse_relative_time(posted_time_str)

        if not success:
            logger.warning(f"Failed to parse posted time: {posted_time_str}, using current UTC time")

        try:
            job_uid = int(job["job_uid"])
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert job_uid to integer: {job['job_uid']}. Error: {e}")
            job_uid = 0  # or you might want to skip this job entirely

        # Rating comes as a string 4.92 or 4.54, I need the resulting float to be with two decimal points
        rating = float(job.get("client_info", {}).get("rating", 0))
        status = "scraped"
        if rating > 0 and rating < 4:
            status = "low_rating"

        processed_job = {
            "job_uid": job_uid,
            "job_title": job["job_title"],
            "job_url": job["job_url"],
            "posted_time": job["posted_time"],
            "posted_time_date": posted_time.isoformat(),  # Already in UTC from parse_relative_time
            "description": job.get("description", ""),
            "location": job.get("client_info", {}).get("location", ""),
            "rating": rating,
            "total_feedback": job.get("client_info", {}).get("total_feedback", ""),
            "spent": job.get("client_info", {}).get("spent", ""),
            "budget": job.get("job_details", {}).get("budget", ""),
            "job_type": job.get("job_details", {}).get("job_type", ""),
            "client_info": str(job.get("client_info", {})),
            "job_details": str(job.get("job_details", {})),
            "skills": str(job.get("skills", [])),
            "proposals": job.get("proposals", ""),
            "status": status,
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
        "--queries",
        type=str,
        nargs="+",  # Accept one or more arguments
        default=DEFAULT_QUERIES,
        help=f"Search queries for jobs (default: {DEFAULT_QUERIES})"
    )

    parser.add_argument(
        "--scraper",
        type=str,
        choices=["crawl4ai", "selenium"],
        default="selenium",
        help="Scraper implementation to use (crawl4ai or selenium)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Maximum number of pages to scrape per query (default: {DEFAULT_MAX_PAGES})"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: False)"
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
    logger.info(f"Search queries: {args.queries}")
    logger.info(f"Max pages per query: {args.max_pages}")
    logger.info(f"Headless mode: {args.headless}")

    try:
        # Initialize authenticator and perform conditional login
        logger.info("Initializing authenticator")
        authenticator = UpworkAuthenticator(
            headless=args.headless
        )
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

        # Process each query
        all_jobs = []
        for query in args.queries:
            logger.info(f"Scraping {args.max_pages} page(s) for query: {query}")
            jobs = await scraper.scrape_jobs(
                query=query,
                max_pages=args.max_pages
            )

            if jobs:
                logger.info(f"Found {len(jobs)} jobs for query: {query}")
                # Process and upload jobs to Baserow
                all_jobs.extend(jobs)
                processed_jobs = await process_jobs_for_baserow(jobs)
                created_rows = await baserow_service.upload_multiple_rows(
                    processed_jobs,
                    deduplicate=True,
                    deduplication_field="job_uid"
                )
                logger.info(f"Successfully uploaded {len(created_rows)} new jobs to Baserow")
            else:
                logger.warning(f"No jobs found for query: {query}")

        if all_jobs:
            # Clean up old rows
            deleted_count = await baserow_service.clean_up_old_rows(days=args.days_to_keep)
            logger.info(f"Cleaned up {deleted_count} old rows from Baserow")
        else:
            logger.warning("No jobs found for any query")

        # Find similar jobs and update status
        await baserow_service.find_similar_jobs(update_status=True)

        logger.info("Upwork Scraper completed successfully")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)