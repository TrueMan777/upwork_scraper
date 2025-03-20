from selenium_driverless.webdriver import Chrome, ChromeOptions
from selenium_driverless.types.by import By
import asyncio
import os
from dotenv import load_dotenv
import json

# Load environment variables from a .env file
load_dotenv()

async def login_to_upwork():
    options = ChromeOptions()
    options.headless = True  # Set to True in production
    options.stealth = True
    # If you need a proxy:
    # options.proxy = "your_proxy_here"

    # Add arguments to handle network issues better
    options.add_arguments(
        "--disable-auto-reload",
        "--disable-background-networking",
        "--no-first-run",  # documented in options.py
        "--disable-infobars",  # documented in options.py
        "--homepage=about:blank",  # documented in options.py
    )

    async with Chrome(options=options, debug=True, timeout=30) as driver:
        await driver.get("https://www.upwork.com/ab/account-security/login", timeout=90, wait_load=False)
        await asyncio.sleep(20)  # Natural pause

        # Wait for and fill username
        username_field = await driver.find_element(By.NAME, "login[username]")
        await username_field.send_keys(os.getenv("UPWORK_EMAIL"))  # Slow typing
        await asyncio.sleep(2)  # Natural pause

        # Click continue
        continue_button = await driver.find_element(By.ID, "login_password_continue")
        await continue_button.click()
        await asyncio.sleep(2)  # Wait for password field

        # Fill password
        password_field = await driver.find_element(By.NAME, "login[password]")
        await password_field.send_keys(os.getenv("UPWORK_PASSWORD"))
        await asyncio.sleep(2)

        # Submit
        submit_button = await driver.find_element(By.ID, "login_control_continue")
        await submit_button.click()

        # Wait for successful login
        await asyncio.sleep(2)

        # Check if asking for security answer. Don't fail when field not found
        try:
            security_answer_field = await driver.find_element(By.ID, "login_answer", timeout=5)
            if security_answer_field:
                print("Security answer field found")
            # Fill security answer
            await security_answer_field.send_keys(os.getenv("UPWORK_SECURITY_ANSWER"))
            await asyncio.sleep(2)
            # Submit
            submit_button = await driver.find_element(By.ID, "login_control_continue", timeout=5)
            await submit_button.click()
        except:
            print("No security answer field found")

        await asyncio.sleep(10)

        # Get cookies
        cookies = await driver.get_cookies()
        print(cookies)
        # Save cookies
        with open("upwork_cookies_selenium.json", "w") as f:
            json.dump(cookies, f)

        print("Login successful")
        # expects URL https://www.upwork.com/nx/find-work/best-matches
        await driver.quit()


if __name__ == "__main__":
    asyncio.run(login_to_upwork())
