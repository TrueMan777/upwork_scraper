"""
Upwork job scraper module.

This module contains the JobsScraper class for scraping Upwork job listings
and the extraction strategy for parsing job data.
"""

import json
import os
import sys
import asyncio
import logging
from datetime import datetime
import pytz
from typing import Dict, Any, List, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, JsonCssExtractionStrategy

# Import the helper function
from upwork_scraper.utils.helpers import save_jobs_to_file

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CustomJsonCssExtractionStrategy(JsonCssExtractionStrategy):
    """Custom extraction strategy that extends JsonCssExtractionStrategy with text content support."""

    def __init__(self, schema: Dict[str, Any], **kwargs):
        """Initialize the custom extraction strategy.

        Args:
            schema: The extraction schema.
            **kwargs: Additional arguments.
        """
        self.text_content = kwargs.get("text_content", False)
        kwargs["input_format"] = "html"  # Force HTML input
        super().__init__(schema, **kwargs)

    def _get_element_text(self, element) -> str:
        """Get the text content of an element.

        Args:
            element: The HTML element.

        Returns:
            The text content of the element.
        """
        if self.text_content:
            # Get all text nodes and normalize spaces
            texts = []
            for text in element.stripped_strings:
                texts.append(text.strip())
            return " ".join(filter(None, texts))  # Filter out empty strings
        return super()._get_element_text(element)


class JobsScraperCrawl4ai:
    """Scraper for Upwork job listings."""

    def __init__(
        self,
        cookies_file: str,
        output_dir: str = "jobs",
        headless: bool = True,
        verbose: bool = True
    ):
        """Initialize the JobsScraper.

        Args:
            cookies_file: Path to the cookies file.
            output_dir: Directory to save job data.
            headless: Whether to run the browser in headless mode.
            verbose: Whether to enable verbose logging.
        """
        self.cookies_file = cookies_file
        self.output_dir = output_dir
        self.headless = headless
        self.verbose = verbose

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Setup job extraction schema
        self.extraction_schema = self._get_extraction_schema()

        logger.info(f"JobsScraper initialized with cookies file: {cookies_file}")

    def _get_extraction_schema(self) -> Dict[str, Any]:
        """Get the extraction schema for job listings.

        Returns:
            The extraction schema.
        """
        return {
            "name": "Jobs",
            "baseSelector": "article.job-tile",    # Base element for each job
            "baseFields": [
                {
                    "name": "job_uid",
                    "type": "attribute",
                    "attribute": "data-ev-job-uid"
                }
            ],
            "fields": [
                {
                    "name": "job_title",
                    "selector": "h2.job-tile-title a",
                    "type": "text"
                },
                {
                    "name": "job_url",
                    "selector": "h2.job-tile-title a",
                    "attribute": "href",
                    "type": "attribute"
                },
                {
                    "name": "posted_time",
                    "selector": "small[data-test=\"job-pubilshed-date\"] span:last-child",
                    "type": "text"
                },
                {
                    "name": "description",
                    "selector": "div[data-test=\"UpCLineClamp JobDescription\"] p",
                    "type": "text"
                },
                {
                    "name": "client_info",
                    "type": "nested",
                    "selector": "ul[data-test=\"JobInfoClient\"]",
                    "fields": [
                        {
                            "name": "payment_verified",
                            "selector": "li[data-test=\"payment-verified\"] .air3-badge-tagline",
                            "type": "text"
                        },
                        {
                            "name": "rating",
                            "selector": ".air3-rating-value-text",
                            "type": "text"
                        },
                        {
                            "name": "total_feedback",
                            "selector": "li[data-test=\"total-feedback\"] div.air3-popper-content div",
                            "type": "text"
                        },
                        {
                            "name": "spent",
                            "selector": ".air3-badge-tagline strong",
                            "type": "text"
                        },
                        {
                            "name": "location",
                            "selector": "li[data-test=\"location\"] div.air3-badge-tagline",
                            "type": "text"
                        }
                    ]
                },
                {
                    "name": "job_details",
                    "type": "nested",
                    "selector": "ul[data-test=\"JobInfo\"]",
                    "fields": [
                        {
                            "name": "job_type",
                            "selector": "li[data-test=\"job-type-label\"] strong",
                            "type": "text"
                        },
                        {
                            "name": "experience_level",
                            "selector": "li[data-test=\"experience-level\"] strong",
                            "type": "text"
                        },
                        {
                            "name": "budget",
                            "selector": "li[data-test=\"is-fixed-price\"] strong:last-child",
                            "type": "text"
                        },
                        {
                            "name": "duration",
                            "selector": "li[data-test=\"duration-label\"] strong:last-child",
                            "type": "text"
                        }
                    ]
                },
                {
                    "name": "skills",
                    "selector": "div.air3-token-container button.air3-token span",
                    "type": "list",
                    "fields": [
                        {
                            "name": "skill",
                            "type": "text"
                        }
                    ]
                },
                {
                    "name": "proposals",
                    "selector": "li[data-test=\"proposals-tier\"] strong",
                    "type": "text"
                }
            ]
        }

    def _load_cookies(self) -> List[Dict[str, Any]]:
        """Load cookies from the cookies file.

        Returns:
            List of cookie dictionaries.

        Raises:
            FileNotFoundError: If the cookies file is not found.
        """
        try:
            with open(self.cookies_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Cookies file not found: {self.cookies_file}")
            raise

    async def scrape_jobs(
        self,
        query: str,
        max_pages: int = 1,
        sort_by: str = "recency",
        client_hires_filter: str = "1-9,10-"
    ) -> List[Dict[str, Any]]:
        """Scrape job listings from Upwork.

        Args:
            query: Search query for jobs.
            max_pages: Maximum number of pages to scrape.
            sort_by: Sort order for results (e.g., "recency").
            client_hires_filter: Filter for client hires.

        Returns:
            List of job data dictionaries.
        """
        all_jobs = []

        try:
            cookies = self._load_cookies()

            browser_config = BrowserConfig(
                verbose=self.verbose,
                headless=self.headless,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                cookies=cookies
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Create the extraction strategy
                extraction_strategy = CustomJsonCssExtractionStrategy(
                    self.extraction_schema,
                    verbose=self.verbose,
                    text_content=True
                )

                run_config = CrawlerRunConfig(
                    wait_for="css:article.job-tile",  # Wait for job listings to appear instead of avatar
                    page_timeout=40000,
                    delay_before_return_html=2.5,
                    cache_mode=CacheMode.BYPASS,
                    extraction_strategy=extraction_strategy,
                )

                for page in range(1, max_pages + 1):
                    # Navigate to the search page
                    url = f"https://www.upwork.com/nx/search/jobs/?q={query}&sort={sort_by}&page={page}&client_hires={client_hires_filter}"
                    logger.info(f"Scraping page {page} with URL: {url}")

                    result = await crawler.arun(url=url, config=run_config)

                    if not result.success:
                        logger.error(f"Crawl failed on page {page}: {result.error_message}")
                        continue

                    # Parse the extracted JSON
                    try:
                        jobs = json.loads(result.extracted_content)
                        logger.info(f"Extracted {len(jobs)} job entries from page {page}")
                        all_jobs.extend(jobs)

                        # Add a small delay between pages
                        if page < max_pages:
                            await asyncio.sleep(2)

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse job data on page {page}: {str(e)}")
                        # Save raw HTML for debugging
                        with open(f'{self.output_dir}/error_page_{page}.html', 'w') as f:
                            f.write(result.html)

            # Save all combined results
            if all_jobs:
                save_jobs_to_file(all_jobs, self.output_dir, "all")

            return all_jobs

        except Exception as e:
            logger.error(f"Error occurred during job scraping: {str(e)}")
            return []


async def example_usage():
    """Example of how to use the JobsScraper."""
    scraper = JobsScraperCrawl4ai(cookies_file="upwork_cookies_selenium.json")

    # Scrape Python web scraping jobs
    jobs = await scraper.scrape_jobs(
        query="web scraping",
        max_pages=2
    )

    print(f"Scraped a total of {len(jobs)} jobs")

    # Display the first job
    if jobs:
        print("\nFirst job details:")
        first_job = jobs[0]
        print(f"Title: {first_job.get('job_title')}")
        print(f"URL: {first_job.get('job_url')}")
        print(f"Posted: {first_job.get('posted_time')}")
        print(f"Skills: {first_job.get('skills')}")


if __name__ == "__main__":
    # Run the example usage
    asyncio.run(example_usage())