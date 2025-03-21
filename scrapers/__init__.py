"""
Scrapers module for Upwork Scraper.

This module contains different scraper implementations for Upwork job listings.
"""

from .jobs_scraper_crawl4ai import JobsScraperCrawl4ai
from .jobs_scraper_selenium import JobsScraperSelenium

__all__ = ["JobsScraperCrawl4ai", "JobsScraperSelenium"]
