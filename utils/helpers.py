"""
Utility functions for the Upwork Scraper.

This module provides utility functions that are used across the project.
"""

import os
import json
import logging
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any, Optional, List, Tuple

# Set up logging
def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "%(asctime)s - %(levelname)s - %(message)s ||| <%(name)s>"
):
    """Set up logging for the application.

    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: The path to the log file. If None, logs to console only.
        log_format: The format string for log messages.

    Returns:
        A configured logger instance.
    """
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    # Basic configuration
    logging_config = {
        'level': numeric_level,
        'format': log_format,
    }

    # Add file handler if specified
    if log_file:
        logging_config['filename'] = log_file
        logging_config['filemode'] = 'a'  # Append to the log file

    # Apply configuration
    logging.basicConfig(**logging_config)

    # Return root logger
    return logging.getLogger()


def load_json_file(file_path: str, default: Any = None) -> Any:
    """Load a JSON file.

    Args:
        file_path: The path to the JSON file.
        default: The default value to return if the file doesn't exist or is invalid.

    Returns:
        The parsed JSON data, or the default value if the file doesn't exist or is invalid.
    """
    try:
        if not os.path.exists(file_path):
            return default

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading JSON file {file_path}: {str(e)}")
        return default


def save_json_file(file_path: str, data: Any, indent: int = 2) -> bool:
    """Save data to a JSON file.

    Args:
        file_path: The path to the JSON file.
        data: The data to save.
        indent: The indentation level for the JSON file.

    Returns:
        True if the data was saved successfully, False otherwise.
    """
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error saving JSON file {file_path}: {str(e)}")
        return False


def is_file_older_than(file_path: str, days: int) -> bool:
    """Check if a file is older than a specified number of days.

    Args:
        file_path: The path to the file.
        days: The number of days.

    Returns:
        True if the file is older than the specified number of days, False otherwise.
    """
    if not os.path.exists(file_path):
        return True

    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    cutoff_time = datetime.now() - timedelta(days=days)

    return file_time < cutoff_time


def ensure_directory_exists(directory_path: str) -> bool:
    """Ensure that a directory exists, creating it if necessary.

    Args:
        directory_path: The path to the directory.

    Returns:
        True if the directory exists or was created successfully, False otherwise.
    """
    try:
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        return True
    except Exception as e:
        logging.error(f"Error creating directory {directory_path}: {str(e)}")
        return False


def format_timestamp(dt: Optional[datetime] = None, format_str: str = "%Y%m%d_%H%M%S") -> str:
    """Format a timestamp string.

    Args:
        dt: The datetime object. If None, uses the current datetime.
        format_str: The format string for the timestamp.

    Returns:
        A formatted timestamp string.
    """
    dt = dt or datetime.now()
    return dt.strftime(format_str)


def generate_filename(prefix: str, extension: str, timestamp: Optional[str] = None) -> str:
    """Generate a filename with a timestamp.

    Args:
        prefix: The prefix for the filename.
        extension: The file extension.
        timestamp: The timestamp string. If None, generates a new timestamp.

    Returns:
        A filename string.
    """
    timestamp = timestamp or format_timestamp()
    extension = extension.lstrip('.')
    return f"{prefix}_{timestamp}.{extension}"


def parse_config_file(config_file: str) -> Dict[str, Any]:
    """Parse a configuration file.

    Args:
        config_file: The path to the configuration file.

    Returns:
        A dictionary of configuration values.
    """
    if not os.path.exists(config_file):
        return {}

    if config_file.endswith('.json'):
        return load_json_file(config_file, {})
    elif config_file.endswith('.py'):
        # Get the directory containing the config file
        config_dir = os.path.dirname(os.path.abspath(config_file))

        # Add the directory to sys.path if it's not already there
        import sys
        if config_dir not in sys.path:
            sys.path.insert(0, config_dir)

        try:
            # Get the module name without the .py extension
            module_name = os.path.basename(config_file)[:-3]

            # Import the module
            config_module = __import__(module_name)

            # Extract all uppercase variables (standard for config)
            config = {
                key: getattr(config_module, key)
                for key in dir(config_module)
                if key.isupper()
            }

            return config
        except Exception as e:
            logging.error(f"Error parsing Python config file {config_file}: {str(e)}")
            return {}
    else:
        logging.error(f"Unsupported config file format: {config_file}")
        return {}


def save_jobs_to_file(jobs: List[Dict[str, Any]], output_dir: str, suffix: str = "") -> str:
    """Save job data to a JSON file.

    Args:
        jobs: List of job data dictionaries.
        output_dir: Directory to save the file in.
        suffix: Suffix to add to the filename.

    Returns:
        Path to the saved file.
    """
    if not jobs:
        logging.warning("No jobs to save")
        return ""

    # Ensure output directory exists
    ensure_directory_exists(output_dir)

    # Create a timestamped filename
    timezone = pytz.timezone('Asia/Shanghai')
    timestamp = datetime.now(timezone).strftime("%Y%m%d_%H%M%S")

    if suffix:
        filename = f'{output_dir}/extracted_jobs_{suffix}_{timestamp}.json'
    else:
        filename = f'{output_dir}/extracted_jobs_{timestamp}.json'

    # Save to file
    result = save_json_file(filename, jobs, indent=2)

    if result:
        logging.info(f"Saved {len(jobs)} jobs to {filename}")
    else:
        logging.error(f"Failed to save jobs to {filename}")

    return filename


def parse_relative_time(time_str: str, reference_time: Optional[datetime] = None) -> Tuple[datetime, bool]:
    """Parse a relative time string (e.g., '2 hours ago', '1 day ago') into a UTC datetime object.

    Args:
        time_str: A string describing a relative time (e.g., '2 hours ago', '57 minutes ago')
        reference_time: The reference time to calculate from (defaults to current UTC time)

    Returns:
        A tuple of (UTC datetime object, bool) where the bool indicates success
    """
    if reference_time is None:
        reference_time = datetime.now(pytz.UTC)
    elif reference_time.tzinfo is None:
        # If reference_time is naive, assume it's UTC and make it aware
        reference_time = pytz.UTC.localize(reference_time)

    if time_str == "yesterday":
        result = reference_time - timedelta(days=1)
        return result, True
    elif time_str == "last week":
        result = reference_time - timedelta(weeks=1)
        return result, True
    elif time_str == "last month":
        result = reference_time - timedelta(days=30)
        return result, True
    elif time_str == "last year":
        result = reference_time - timedelta(days=365)
        return result, True

    # Extract number and unit from the string
    parts = time_str.split()
    if len(parts) >= 3 and parts[-1] == "ago":
        try:
            number = int(parts[0])
            unit = parts[1]

            if unit in ["hour", "hours"]:
                result = reference_time - timedelta(hours=number)
            elif unit in ["minute", "minutes"]:
                result = reference_time - timedelta(minutes=number)
            elif unit in ["day", "days"]:
                result = reference_time - timedelta(days=number)
            elif unit in ["week", "weeks"]:
                result = reference_time - timedelta(weeks=number)
            elif unit in ["month", "months"]:
                # Approximate a month as 30 days
                result = reference_time - timedelta(days=number * 30)
            elif unit in ["year", "years"]:
                result = reference_time - timedelta(days=number * 365)
            else:
                logging.warning(f"Unknown time unit in: {time_str}")
                return reference_time, False

            return result, True

        except ValueError as e:
            logging.error(f"Error parsing relative time '{time_str}': {e}")
            return reference_time, False
    else:
        logging.warning(f"Unexpected relative time format: {time_str}")
        return reference_time, False