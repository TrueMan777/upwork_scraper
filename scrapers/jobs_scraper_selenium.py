"""
Upwork job scraper module using Selenium Driverless.

This module contains the JobsScraperSelenium class for scraping Upwork job listings
using Selenium Driverless for browser automation.
"""

import json
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import quote_plus
from selenium_driverless import webdriver
from selenium_driverless.types.by import By
from bs4 import BeautifulSoup
import re

# Import the helper function
from upwork_scraper.utils.helpers import save_jobs_to_file, setup_logging

# Set up logging
logger = setup_logging(log_level="INFO")


class JobsScraperSelenium:
    """Scraper for Upwork job listings using Selenium Driverless."""

    def __init__(
        self,
        cookies_file: str,
        output_dir: str = "jobs",
        headless: bool = True,
        verbose: bool = True
    ):
        """Initialize the JobsScraperSelenium.

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

        # User agent for browser
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

        logger.info(f"JobsScraperSelenium initialized with cookies file: {cookies_file}")

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

    async def _init_driver(self) -> webdriver.Chrome:
        """Initialize the Selenium Driverless Chrome driver.

        Returns:
            A configured Chrome driver instance.
        """
        options = webdriver.ChromeOptions()
        options.headless = self.headless
        options.stealth = True

        # Add arguments to handle network issues better
        options.add_arguments(
            "--disable-auto-reload",
            "--disable-background-networking",
            "--no-first-run",
            "--disable-infobars",
            "--homepage=about:blank",
        )

        # Create and return the driver
        driver = await webdriver.Chrome(options=options).__aenter__()
        return driver

    async def _add_cookies(self, driver: webdriver.Chrome):
        """Add cookies to the driver.

        Args:
            driver: The Selenium driver instance.
        """
        cookies = self._load_cookies()

        # Navigate to domain first (required to set cookies)
        await driver.get("https://www.upwork.com", wait_load=False)
        await asyncio.sleep(10)

        # Add each cookie to the driver
        for cookie in cookies:
            # Format cookie for Selenium
            cookie_dict = {
                "name": cookie["name"],
                "value": cookie["value"],
                "domain": cookie.get("domain", ".upwork.com"),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", True),
                "httpOnly": cookie.get("httpOnly", False)
            }

            # Set expiry if available
            if "expirationDate" in cookie:
                cookie_dict["expiry"] = int(cookie["expirationDate"])

            try:
                await driver.add_cookie(cookie_dict)
            except Exception as e:
                if self.verbose:
                    logger.warning(f"Failed to add cookie {cookie['name']}: {str(e)}")
                continue

    async def scrape_jobs(
        self,
        query: str,
        max_pages: int = 1,
        sort_by: str = "recency",
        client_hires_filter: str = "1-9,10-",
        proposals: str = "0-4,5-9,10-14",
        location: str = "Australia%2520and%2520New%2520Zealand,Hong%2520Kong,Israel,Saudi%2520Arabia,Japan,Macao,Malaysia,Singapore,South%2520Korea,Thailand",
        payment_verified: str = "1",
    ) -> List[Dict[str, Any]]:
        """Scrape job listings from Upwork.

        Args:
            query: Search query for jobs.
            max_pages: Maximum number of pages to scrape.
            sort_by: Sort order for results (e.g., "recency").
            client_hires_filter: Filter for client hires.
            proposals: Filter for proposals.
            location: Filter for location.
            payment_verified: Filter for payment verified.

        Returns:
            List of job data dictionaries.
        """
        all_jobs = []

        try:
            # Initialize driver
            driver = await self._init_driver()

            try:
                # Add cookies to the driver
                await self._add_cookies(driver)

                # Refesh once cookies are loaded
                await driver.get("https://www.upwork.com", wait_load=False)
                await asyncio.sleep(10)

                for page in range(1, max_pages + 1):
                    # Build URL for the page
                    encoded_query = quote_plus(query)
                    url = f"https://www.upwork.com/nx/search/jobs/?q={encoded_query}&sort={sort_by}&page={page}&client_hires={client_hires_filter}&proposals={proposals}&location={location}&payment_verified={payment_verified}"
                    logger.info(f"Scraping page {page} with URL: {url}")

                    # Navigate to the URL
                    await driver.get(url, wait_load=False)
                    await asyncio.sleep(10)

                    # Wait for job listings to appear
                    try:
                        logger.info("Waiting for job listings to load...")
                        await driver.find_element(By.CSS_SELECTOR, "article.job-tile", timeout=30)
                    except Exception as e:
                        logger.error(f"Timed out waiting for job listings on page {page}: {str(e)}")

                        # Save page source for debugging
                        if self.verbose:
                            html = await driver.page_source
                            debug_file = f'{self.output_dir}/debug_page_{page}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
                            with open(debug_file, 'w') as f:
                                f.write(html)
                            logger.info(f"Saved debug HTML to {debug_file}")

                        continue

                    # Make sure the page is fully loaded
                    await asyncio.sleep(3)

                    if self.verbose:
                        # Save HTML for debugging
                        html = await driver.page_source
                        debug_file = f'{self.output_dir}/debug_page_{page}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
                        with open(debug_file, 'w') as f:
                            f.write(html)
                        logger.info(f"Saved debug HTML to {debug_file}")
                        # Take screenshot
                        screenshot_file = f'{self.output_dir}/screenshot_page_{page}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
                        await driver.get_screenshot_as_file(screenshot_file)
                        logger.info(f"Saved screenshot to {screenshot_file}")

                    # Get page source and parse jobs
                    html = await driver.page_source
                    jobs = await self._parse_jobs(html)

                    logger.info(f"Extracted {len(jobs)} job entries from page {page}")
                    if len(jobs) > 0 and jobs[0].get("client_info", {}).get("location", "") == "":
                        logger.warning(f"No location found for job {jobs[0].get('job_title')}")
                        logger.warning(f"Job data: {jobs[0]}")

                    # Save page results to file for inspection
                    if jobs:
                        all_jobs.extend(jobs)

                    # Add a small delay between pages
                    if page < max_pages:
                        await asyncio.sleep(2)

                # Save all combined results
                if all_jobs:
                    save_jobs_to_file(all_jobs, self.output_dir, "all")

                return all_jobs

            finally:
                # Close the driver
                await driver.__aexit__(None, None, None)

        except Exception as e:
            logger.error(f"Error occurred during job scraping: {str(e)}")
            return []

    async def _parse_jobs(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse job listings from HTML content.

        Args:
            html_content: The HTML content to parse.

        Returns:
            List of job data dictionaries.
        """
        jobs = []

        try:
            # Helper method to clean text by normalizing spaces
            def _clean_text(element_or_text) -> str:
                """Clean text by replacing HTML elements with spaces and normalizing spaces.

                Args:
                    element_or_text: BeautifulSoup element or string to clean.

                Returns:
                    Cleaned text with normalized spaces.
                """
                if not element_or_text:
                    return ""

                # Handle both string and BeautifulSoup element
                if hasattr(element_or_text, 'get_text'):
                    # This is a BeautifulSoup element, get its text with appropriate spacing
                    text = ' '.join([s.strip() for s in element_or_text.stripped_strings])
                else:
                    # This is already a string
                    text = str(element_or_text)

                # Replace HTML tags with spaces (for any leftover HTML)
                text = re.sub(r'<[^>]+>', ' ', text)
                # Replace multiple spaces with a single space
                text = re.sub(r'\s+', ' ', text)
                return text.strip()

            # Helper method to clean text but preserve paragraph breaks
            def _clean_text_with_paragraphs(element_or_text) -> str:
                """Clean text by replacing HTML elements with spaces while preserving paragraph breaks.

                Args:
                    element_or_text: BeautifulSoup element or string to clean.

                Returns:
                    Cleaned text with normalized spaces and preserved paragraphs.
                """
                if not element_or_text:
                    return ""

                # Handle both string and BeautifulSoup element
                if hasattr(element_or_text, 'get_text'):
                    # For elements, get the HTML content first
                    html_content = str(element_or_text)

                    # Replace paragraph-like tags with markers before getting text
                    paragraph_tags = ['p', 'div', 'br', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
                    for tag in paragraph_tags:
                        # Close tags (</p>) - add two newlines after
                        html_content = re.sub(f'</{tag}>', f'</{ tag }>\n\n', html_content, flags=re.IGNORECASE)
                        # Self-closing tags (<br/>) - add two newlines
                        html_content = re.sub(f'<{tag}[^>]*/>', f'<{tag}/>\n\n', html_content, flags=re.IGNORECASE)

                    # Create a new soup object with the modified HTML
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Get text with appropriate spacing
                    text = soup.get_text()
                else:
                    # This is already a string
                    text = str(element_or_text)

                # Replace HTML tags with spaces (for any leftover HTML)
                text = re.sub(r'<[^>]+>', ' ', text)

                # Normalize spaces (but preserve consecutive newlines)
                # First, replace multiple spaces with a single space
                text = re.sub(r'[ \t]+', ' ', text)

                # Then, normalize newlines (2+ newlines become exactly 2 newlines)
                text = re.sub(r'\n{3,}', '\n\n', text)

                # Finally, trim spaces at the beginning and end of each line
                lines = [line.strip() for line in text.split('\n')]
                text = '\n'.join(lines)

                return text.strip()

            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all job tiles
            job_tiles = soup.select('article.job-tile')
            logger.info(f"Found {len(job_tiles)} job tiles in the HTML")

            for job_tile in job_tiles:
                try:
                    job_data = {}

                    # Get job UID
                    job_data["job_uid"] = job_tile.get('data-ev-job-uid', '')

                    # Get job title and URL
                    title_element = job_tile.select_one('h2.job-tile-title a')
                    if title_element:
                        job_data["job_title"] = _clean_text(title_element)
                        job_data["job_url"] = title_element.get('href', '')

                        # Make absolute URL if needed
                        if job_data["job_url"] and not job_data["job_url"].startswith('http'):
                            job_data["job_url"] = f"https://www.upwork.com{job_data['job_url']}"

                    # Get posted time
                    posted_time_element = job_tile.select_one('small[data-test="job-pubilshed-date"] span:last-child')
                    if posted_time_element:
                        job_data["posted_time"] = _clean_text(posted_time_element)

                    # Get description
                    description_element = job_tile.select_one('div[data-test="UpCLineClamp JobDescription"] p')
                    if description_element:
                        job_data["description"] = _clean_text_with_paragraphs(description_element)

                    # Try to get the full description container if the p element doesn't contain all content
                    if not description_element:
                        description_container = job_tile.select_one('div[data-test="UpCLineClamp JobDescription"]')
                        if description_container:
                            job_data["description"] = _clean_text_with_paragraphs(description_container)

                    # Get client info
                    client_info = {}
                    client_info_element = job_tile.select_one('ul[data-test="JobInfoClient"]')
                    if client_info_element:
                        # Payment verified
                        payment_element = client_info_element.select_one('li[data-test="payment-verified"] .air3-badge-tagline')
                        if payment_element:
                            client_info["payment_verified"] = _clean_text(payment_element)

                        # Rating
                        rating_element = client_info_element.select_one('.air3-rating-value-text')
                        if rating_element:
                            client_info["rating"] = _clean_text(rating_element)

                        # Feedback
                        feedback_element = client_info_element.select_one('li[data-test="total-feedback"] div.air3-popper-content div')
                        if feedback_element:
                            client_info["total_feedback"] = _clean_text(feedback_element)

                        # Spent
                        spent_element = client_info_element.select_one('.air3-badge-tagline strong')
                        if spent_element:
                            client_info["spent"] = _clean_text(spent_element)

                        # Location
                        location_element = client_info_element.select_one('li[data-test="location"] div.air3-badge-tagline')
                        if location_element:
                            client_info["location"] = _clean_text(location_element)
                    else:
                        logger.warning(f"No client info found for job {job_data.get('job_title')}")

                    job_data["client_info"] = client_info

                    # Get job details
                    job_details = {}
                    job_details_element = job_tile.select_one('ul[data-test="JobInfo"]')
                    if job_details_element:
                        # Job type
                        job_type_element = job_details_element.select_one('li[data-test="job-type-label"] strong')
                        if job_type_element:
                            job_details["job_type"] = _clean_text(job_type_element)

                        # Experience level
                        exp_level_element = job_details_element.select_one('li[data-test="experience-level"] strong')
                        if exp_level_element:
                            job_details["experience_level"] = _clean_text(exp_level_element)

                        # Budget
                        budget_element = job_details_element.select_one('li[data-test="is-fixed-price"] strong:last-child')
                        if budget_element:
                            job_details["budget"] = _clean_text(budget_element)

                        # Duration
                        duration_element = job_details_element.select_one('li[data-test="duration-label"] strong:last-child')
                        if duration_element:
                            job_details["duration"] = _clean_text(duration_element)

                    job_data["job_details"] = job_details

                    # Get skills
                    skills = []
                    skill_elements = job_tile.select('div.air3-token-container button.air3-token span')
                    for skill_element in skill_elements:
                        skill_text = _clean_text(skill_element)
                        if skill_text:
                            skills.append(skill_text)

                    job_data["skills"] = skills

                    # Get proposals
                    proposals_element = job_tile.select_one('li[data-test="proposals-tier"] strong')
                    if proposals_element:
                        job_data["proposals"] = _clean_text(proposals_element)

                    # Only add job if we have the required fields
                    if job_data.get("job_uid") and job_data.get("job_title") and job_data.get("job_url"):
                        jobs.append(job_data)
                    else:
                        logger.warning(f"Skipping job with missing required fields: {job_data}")

                except Exception as e:
                    logger.error(f"Error parsing job tile: {str(e)}")
                    continue

            return jobs

        except Exception as e:
            logger.error(f"Error parsing HTML content: {str(e)}")
            return jobs


async def example_usage():
    """Example of how to use the JobsScraperSelenium."""
    scraper = JobsScraperSelenium(cookies_file="upwork_cookies_selenium.json")

    # Scrape Python web scraping jobs
    jobs = await scraper.scrape_jobs(
        query="web scraping",
        max_pages=1
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