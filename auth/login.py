"""
Authentication module for Upwork login.

This module contains the UpworkAuthenticator class that handles Upwork authentication
with conditional login - only performing login when necessary.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from selenium_driverless.webdriver import Chrome, ChromeOptions
from selenium_driverless.types.by import By
from dotenv import load_dotenv

from utils.helpers import is_file_older_than, load_json_file, save_json_file

# Set up logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class UpworkAuthenticator:
    """Handles Upwork authentication with conditional login."""

    def __init__(
        self,
        cookies_file: str = "upwork_cookies_selenium.json",
        cookie_max_age_days: int = 7,
        headless: bool = True,
    ):
        """Initialize the authenticator.

        Args:
            cookies_file: Path to the cookies file.
            cookie_max_age_days: Maximum age of cookies in days before requiring a new login.
            headless: Whether to run the browser in headless mode.
        """
        self.cookies_file = cookies_file
        self.cookie_max_age_days = cookie_max_age_days
        self.headless = headless
        self.cookies = None
        logger.info(f"Initialized UpworkAuthenticator with cookies file: {cookies_file}")

    async def login_if_needed(self) -> bool:
        """Perform login only if cookies don't exist, are expired, or are invalid.

        Returns:
            True if login was performed, False if existing cookies were used.
        """
        if self._are_cookies_valid():
            logger.info("Using existing valid cookies")
            self.cookies = load_json_file(self.cookies_file, [])
            return False

        logger.info("Cookies are invalid or expired, performing login")
        await self._perform_login()
        return True

    def _are_cookies_valid(self) -> bool:
        """Check if cookies exist and are valid.

        Returns:
            True if cookies are valid, False otherwise.
        """
        # Check if file exists
        if not os.path.exists(self.cookies_file):
            logger.info(f"Cookies file not found: {self.cookies_file}")
            return False

        # Check if file is too old
        if is_file_older_than(self.cookies_file, self.cookie_max_age_days):
            logger.info(f"Cookies are older than {self.cookie_max_age_days} days")
            return False

        # Validate cookie contents
        try:
            cookies = load_json_file(self.cookies_file, [])
            if not cookies or not isinstance(cookies, list) or len(cookies) == 0:
                logger.warning("Cookies file exists but contains no valid cookies")
                return False

            # Check for essential cookies
            essential_cookies = ["XSRF-TOKEN", "visitor_id", "upwork_ws_access_token"]
            cookie_names = [cookie.get("name") for cookie in cookies if "name" in cookie]

            # Check if at least one essential cookie is present
            if not any(name in cookie_names for name in essential_cookies):
                logger.warning("Cookies file exists but essential cookies are missing")
                return False

            # Check for expired cookies
            now_timestamp = datetime.now().timestamp()
            for cookie in cookies:
                if "expiry" in cookie and cookie["expiry"] < now_timestamp:
                    logger.info("At least one cookie has expired")
                    return False

            logger.info("Cookies exist and appear to be valid")
            return True

        except Exception as e:
            logger.error(f"Error validating cookies: {e}")
            return False

    async def _perform_login(self):
        """Perform the login process and save cookies."""
        logger.info("Starting Upwork login process")

        options = ChromeOptions()
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

        try:
            async with Chrome(options=options, debug=True, timeout=30) as driver:
                # Navigate to login page
                logger.info("Navigating to Upwork login page")
                await driver.get("https://www.upwork.com/ab/account-security/login", timeout=90, wait_load=False)
                await asyncio.sleep(20)  # Wait for page to load

                # Get required environment variables
                email = os.getenv("UPWORK_EMAIL")
                password = os.getenv("UPWORK_PASSWORD")
                security_answer = os.getenv("UPWORK_SECURITY_ANSWER")

                if not email or not password:
                    raise ValueError("UPWORK_EMAIL and UPWORK_PASSWORD environment variables must be set")

                # Enter email
                logger.info("Entering email")
                username_field = await driver.find_element(By.NAME, "login[username]")
                await username_field.send_keys(email)
                await asyncio.sleep(2)

                # Click continue
                continue_button = await driver.find_element(By.ID, "login_password_continue")
                await continue_button.click()
                await asyncio.sleep(2)

                # Enter password
                logger.info("Entering password")
                password_field = await driver.find_element(By.NAME, "login[password]")
                await password_field.send_keys(password)
                await asyncio.sleep(2)

                # Submit
                submit_button = await driver.find_element(By.ID, "login_control_continue")
                await submit_button.click()
                await asyncio.sleep(2)

                # Check if security answer is required
                try:
                    security_answer_field = await driver.find_element(By.ID, "login_answer", timeout=5)
                    if security_answer_field:
                        logger.info("Security answer field found")

                        if not security_answer:
                            raise ValueError("UPWORK_SECURITY_ANSWER environment variable must be set")

                        # Enter security answer
                        await security_answer_field.send_keys(security_answer)
                        await asyncio.sleep(2)

                        # Submit
                        submit_button = await driver.find_element(By.ID, "login_control_continue", timeout=5)
                        await submit_button.click()
                        await asyncio.sleep(2)
                except Exception as e:
                    logger.info(f"No security answer field found or error processing it: {e}")

                # Wait for login to complete
                await asyncio.sleep(10)

                # Get cookies
                self.cookies = await driver.get_cookies()
                logger.info(f"Retrieved {len(self.cookies)} cookies")

                # Save cookies
                if self.cookies:
                    save_json_file(self.cookies_file, self.cookies)
                    logger.info(f"Cookies saved to {self.cookies_file}")
                else:
                    logger.error("No cookies were retrieved")

                # Validate login success
                try:
                    # Fix: Use await for current_url since it might be an async property
                    current_url = await driver.current_url
                    if "find-work" in current_url or "my-jobs" in current_url:
                        logger.info("Login successful, verified by URL")
                    else:
                        logger.warning(f"Login may have failed. Current URL: {current_url}")
                except Exception as e:
                    logger.warning(f"Could not verify login success via URL: {e}")
                    # Continue anyway since we have cookies

        except Exception as e:
            logger.error(f"Error during login process: {e}")
            raise

    def get_cookies(self) -> List[Dict[str, Any]]:
        """Get the current cookies.

        Returns:
            A list of cookie dictionaries.
        """
        if not self.cookies:
            self.cookies = load_json_file(self.cookies_file, [])
        return self.cookies


# Example usage
async def example_usage():
    """Example of how to use the UpworkAuthenticator."""
    authenticator = UpworkAuthenticator()

    # This will only perform login if needed
    login_performed = await authenticator.login_if_needed()

    if login_performed:
        print("Login was performed because cookies were invalid or expired")
    else:
        print("Used existing valid cookies")

    cookies = authenticator.get_cookies()
    print(f"Number of cookies: {len(cookies)}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the example
    asyncio.run(example_usage())