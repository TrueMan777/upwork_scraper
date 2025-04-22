#!/usr/bin/env python3
"""
Script to find and optionally delete duplicate jobs in Baserow database.
"""

import os
import sys
import asyncio
import logging
import argparse
from typing import Dict, List, Any
from dotenv import load_dotenv

# Add the parent directory to sys.path to enable imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from upwork_scraper.data.baserow import BaserowService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s ||| <%(name)s>"
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Find and manage duplicate jobs in Baserow")

    parser.add_argument(
        "--find-duplicates",
        action="store_true",
        help="Find duplicate entries"
    )

    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete duplicate entries after finding them"
    )

    parser.add_argument(
        "--keep-oldest",
        action="store_true",
        help="When deleting, keep the oldest entry instead of the newest"
    )

    parser.add_argument(
        "--update-similar-jobs",
        action="store_true",
        help="Update the status of similar jobs to 'duplicate'"
    )

    return parser.parse_args()

async def print_duplicate_details(duplicates: Dict[str, List[Dict[str, Any]]]):
    """Print detailed information about duplicate entries."""
    if not duplicates:
        logger.info("No duplicates found!")
        return

    logger.info(f"\nFound {len(duplicates)} job_uids with duplicates:")
    for job_uid, rows in duplicates.items():
        logger.info(f"\nJob UID: {job_uid}")
        logger.info(f"Number of duplicates: {len(rows)}")

        for row in rows:
            logger.info(
                f"  - Row ID: {row.get('id', 'N/A')}\n"
                f"    Title: {row.get('job_title', 'N/A')}\n"
                f"    Posted: {row.get('posted_time_date', 'N/A')}\n"
                f"    URL: {row.get('job_url', 'N/A')}"
            )

async def main():
    """Main function to find and manage duplicates."""
    # Load environment variables
    load_dotenv()

    # Parse arguments
    args = parse_arguments()

    try:
        # Initialize Baserow service
        baserow = BaserowService()

        if args.find_duplicates:
            # Find duplicates
            logger.info("Searching for duplicates...")
            duplicates = await baserow.find_duplicates()
            # Print duplicate details
            await print_duplicate_details(duplicates)

        # Find similar jobs and update status
        await baserow.find_similar_jobs(update_status=args.update_similar_jobs)

        # Delete duplicates if requested
        if args.delete and duplicates:
            keep_newest = not args.keep_oldest
            logger.info(f"\nDeleting duplicates, keeping {'oldest' if args.keep_oldest else 'newest'} entries...")
            deleted_count = await baserow.delete_duplicates(keep_newest=keep_newest)
            logger.info(f"Successfully deleted {deleted_count} duplicate rows")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)