import json
from crawl4ai import AsyncWebCrawler
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, JsonCssExtractionStrategy
import asyncio
from datetime import datetime
import os
import pytz
from typing import Dict, Any, List
import requests
import json
from dotenv import load_dotenv

load_dotenv()
COOKIES_FILE = "upwork_cookies_selenium.json"

class CustomJsonCssExtractionStrategy(JsonCssExtractionStrategy):
    def __init__(self, schema: Dict[str, Any], **kwargs):
        self.text_content = kwargs.get("text_content", False)  # Get from kwargs instead of popping
        kwargs["input_format"] = "html"  # Force HTML input
        super().__init__(schema, **kwargs)

    def _get_element_text(self, element) -> str:
        if self.text_content:
            # Get all text nodes and normalize spaces
            texts = []
            for text in element.stripped_strings:
                texts.append(text.strip())
            return " ".join(filter(None, texts))  # Filter out empty strings
        return super()._get_element_text(element)

async def main():
    try:
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)

        browser_config = BrowserConfig(
            verbose=True,
            headless=True, # Set to True in production
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            cookies=cookies
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:

            # 1. Define a comprehensive extraction schema
            schema = {
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

            # 2. Create the extraction strategy
            extraction_strategy = CustomJsonCssExtractionStrategy(schema, verbose=True, text_content=True)

            run_config = CrawlerRunConfig(
                wait_for="css:.nav-user-avatar",  # Wait for avatar logo to appear
                page_timeout=120000,
                delay_before_return_html=2.5,
                cache_mode=CacheMode.BYPASS,
                # js_only=True, # We're continuing from the open tab
                extraction_strategy=extraction_strategy,
            )
            # Navigate to the search page
            query = "web scraping"
            url = f"https://www.upwork.com/nx/search/jobs/?q={query}&sort=recency&page=1&client_hires=1-9,10-"
            result = await crawler.arun(url=url, config=run_config)

            if not result.success:
                print("Crawl failed:", result.error_message)
                return

            # Parse the extracted JSON
            data = json.loads(result.extracted_content)
            print(f"\nExtracted {len(data)} job entries")
            print("\nFirst job entry:")
            print(json.dumps(data[0], indent=2) if data else "No data found")

            await upload_jobs_to_baserow(data)

            # Save to file for inspection
            timezone = pytz.timezone('Asia/Shanghai')
            timestamp = datetime.now(timezone).strftime("%Y%m%d_%H%M%S")
            # Create jobs directory if it doesn't exist
            os.makedirs("jobs", exist_ok=True)
            # Save to file for inspection
            with open(f'jobs/extracted_jobs_{timestamp}.json', 'w') as f:
                json.dump(data, f, indent=2)
            print("\nSaved all jobs to extracted_jobs.json")

            with open('extracted_jobs.html', 'w') as f:
                f.write(result.html)
    except Exception as e:
        print(f"Error occurred: {str(e)}")


async def upload_jobs_to_baserow(jobs: List[Dict[str, Any]]):
    # Your Baserow API key
    api_key = os.getenv("BASEROW_API_KEY")

    # Your Baserow table ID
    table_id = os.getenv("BASEROW_TABLE_ID")

    baserow_jobs = []
    try:
        # Get all rows
        response = requests.get(
            f"https://api.baserow.io/api/database/rows/table/{table_id}/?user_field_names=true",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json"
            }
        )
        baserow_jobs = response.json()["results"]
    except Exception as e:
        print(f"Error occurred: {str(e)}")

    try:
        # Upload rows one by one
        for job in jobs:
            if job["job_uid"] in [baserow_job["job_uid"] for baserow_job in baserow_jobs]:
                continue
            # Create a new row
            row = {
                "job_uid": job["job_uid"],
                "job_title": job["job_title"],
                "job_url": job["job_url"],
                "posted_time": job["posted_time"],
                "description": job["description"],
                "client_info": str(job["client_info"]),
                "job_details": str(job["job_details"]),
                "skills": str(job["skills"]),
                "proposals": job["proposals"],
            }
            # Upload the row to Baserow
            response = requests.post(
                f"https://api.baserow.io/api/database/rows/table/{table_id}/?user_field_names=true",
                headers={
                    "Authorization": f"Token {api_key}",
                    "Content-Type": "application/json"
                },
                json=row
            )
            # Wait for 1 second before uploading the next row
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error occurred: {str(e)}")

async def clean_up_baserow_jobs():
    # Your Baserow API key
    api_key = os.getenv("BASEROW_API_KEY")

    # Your Baserow table ID
    table_id = os.getenv("BASEROW_TABLE_ID")

    try:
        # Get all rows
        response = requests.get(
            f"https://api.baserow.io/api/database/rows/table/{table_id}/?user_field_names=true",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json"
            }
        )
        baserow_jobs = response.json()["results"]
    except Exception as e:
        print(f"Error occurred: {str(e)}")

    for job in baserow_jobs:
        response = requests.delete(
            f"https://api.baserow.io/api/database/rows/table/{table_id}/{job['id']}/?user_field_names=true",
            headers={"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
        )
        print(f"{job['job_title']} deleted")
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
    # data = json.load(open("jobs/extracted_jobs_20250320_142526.json"))
    # asyncio.run(upload_jobs_to_baserow(data))
    # asyncio.run(clean_up_baserow_jobs())