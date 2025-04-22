import json
import os
from datetime import datetime, timedelta
import requests
from typing import Dict, Any, Optional
import logging
import yaml
import base64
from pathlib import Path
import re
import calendar
import zoneinfo

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_german_summer_time(date_obj: datetime) -> bool:
    """
    Check if the given date is during German summer time (DST).
    
    Args:
        date_obj (datetime): The date to check
        
    Returns:
        bool: True if the date is during German summer time, False otherwise
    """
    # Get the timezone for Germany
    berlin_tz = zoneinfo.ZoneInfo("Europe/Berlin")
    
    # Convert the date to the Berlin timezone
    date_in_berlin = date_obj.astimezone(berlin_tz)
    
    # Check if the date is during DST
    return date_in_berlin.dst() != timedelta(0)

def get_german_timezone_offset(date_obj: datetime) -> str:
    """
    Get the German timezone offset for the given date.
    
    Args:
        date_obj (datetime): The date to get the timezone offset for
        
    Returns:
        str: The timezone offset in format "+HH:MM" or "-HH:MM"
    """
    if is_german_summer_time(date_obj):
        return "+02:00"  # Summer time (DST)
    else:
        return "+01:00"  # Winter time (standard)

def encode_date_to_base64(date_str: str) -> str:
    """
    Encode an ISO8601 date string to Base64 for use with Tibber API.
    Always adds the German timezone based on the date (summer or winter time).
    
    Args:
        date_str (str): Date string in one of these formats:
                        - Full ISO8601 with timezone (e.g., "2024-06-01T00:00:00+02:00")
                        - Date only (e.g., "2024-06-01")
                        - Year and month only (e.g., "2024-05")
        
    Returns:
        str: Base64 encoded date string
    """
    try:
        # Parse the date to determine the timezone
        date_obj = None
        
        # Check if the string contains only year and month (YYYY-MM)
        if len(date_str) == 7 and date_str.count('-') == 1:
            # Add day and time component with milliseconds
            date_str = f"{date_str}-01T00:00:00.000"
            date_obj = datetime.fromisoformat(date_str)
            logger.info(f"Added day and time component to year-month: {date_str}")
        # Check if the string contains only a date (YYYY-MM-DD)
        elif len(date_str) == 10 and date_str.count('-') == 2:
            # Add time component with milliseconds
            date_str = f"{date_str}T00:00:00.000"
            date_obj = datetime.fromisoformat(date_str)
            logger.info(f"Added time component to date: {date_str}")
        # Check if the string contains a date and time but no timezone
        elif len(date_str) >= 19 and 'T' in date_str and ('+' not in date_str and 'Z' not in date_str):
            # Add milliseconds if not present
            if '.' not in date_str:
                date_str = date_str.replace('T00:00:00', 'T00:00:00.000')
            date_obj = datetime.fromisoformat(date_str)
            logger.info(f"Parsed date with time but no timezone: {date_str}")
        # If the string already has a timezone, parse it
        elif '+' in date_str or 'Z' in date_str:
            # Replace Z with +00:00 for parsing
            date_str_for_parsing = date_str.replace('Z', '+00:00')
            # Add milliseconds if not present
            if '.' not in date_str_for_parsing:
                date_str_for_parsing = date_str_for_parsing.replace('T00:00:00', 'T00:00:00.000')
            date_obj = datetime.fromisoformat(date_str_for_parsing)
            logger.info(f"Parsed date with existing timezone: {date_str}")
        
        # If we couldn't parse the date, try to extract year and month
        if date_obj is None:
            match = re.match(r'(\d{4}-\d{2})', date_str)
            if match:
                year_month = match.group(1)
                date_str = f"{year_month}-01T00:00:00.000"
                date_obj = datetime.fromisoformat(date_str)
                logger.info(f"Extracted year-month and created date: {date_str}")
            else:
                raise ValueError(f"Could not parse date: {date_str}")
        
        # Get the German timezone offset
        tz_offset = get_german_timezone_offset(date_obj)
        
        # Add the timezone to the date string if it doesn't have one
        if '+' not in date_str and 'Z' not in date_str:
            date_str = f"{date_str}{tz_offset}"
            logger.info(f"Added German timezone {tz_offset} to date: {date_str}")
        
        # Ensure the date string has milliseconds
        if '.' not in date_str:
            date_str = date_str.replace('T00:00:00', 'T00:00:00.000')
        
        # Validate the date format
        try:
            # Try to parse the date to validate format
            datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected ISO8601 format.")
        
        # Encode to Base64
        encoded = base64.b64encode(date_str.encode('utf-8')).decode('utf-8')
        logger.info(f"Encoded date {date_str} to Base64: {encoded}")
        return encoded
    except Exception as e:
        logger.error(f"Error encoding date to Base64: {e}")
        raise

def extract_year_month(date_str: str) -> str:
    """
    Extract year and month from a date string in various formats.
    
    Args:
        date_str (str): Date string in various formats
        
    Returns:
        str: Year and month in format YYYY-MM
    """
    # Handle Base64 encoded strings
    if date_str.startswith('MjAy') or re.match(r'^[A-Za-z0-9+/=]+$', date_str):
        try:
            # Decode Base64
            decoded = base64.b64decode(date_str).decode('utf-8')
            # Extract year and month
            match = re.match(r'(\d{4}-\d{2})', decoded)
            if match:
                return match.group(1)
        except Exception:
            pass
    
    # Handle ISO8601 and other formats
    match = re.match(r'(\d{4}-\d{2})', date_str)
    if match:
        return match.group(1)
    
    raise ValueError(f"Could not extract year and month from date string: {date_str}")

def calculate_first_parameter(after_date: str) -> int:
    """
    Calculate the 'first' parameter for the Tibber API based on the number of days in the month.
    
    Args:
        after_date (str): Date string in format YYYY-MM or other formats
        
    Returns:
        int: Number of hours to fetch (days in month * 24), capped at 744
    """
    # Extract year and month
    try:
        year_month = extract_year_month(after_date)
        
        # Parse year and month
        year, month = map(int, year_month.split('-'))
        
        # Get number of days in the month
        days_in_month = calendar.monthrange(year, month)[1]
        
        # Calculate hours (days * 24)
        hours = days_in_month * 24
        
        # Cap at 744 (maximum allowed by API)
        return min(hours, 744)
    except (ValueError, IndexError) as e:
        # If parsing fails, use a default value
        logger.warning(f"Could not parse year-month from {after_date}, using default value of 720: {e}")
        return 720

def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    # Get the project root directory (two levels up from this file)
    project_root = Path(__file__).parent.parent
    config_path = project_root / 'config' / 'config.yaml'
    
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

class TibberAPI:
    """Class to handle interactions with the Tibber API."""
    
    def __init__(self, access_token: str):
        """
        Initialize the Tibber API client.
        
        Args:
            access_token (str): The Tibber API access token
        """
        self.access_token = access_token
        self.base_url = "https://api.tibber.com/v1-beta/gql"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

    def get_consumption_data(self, after_date: Optional[str] = None, first: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch consumption data from Tibber API.
        
        Args:
            after_date (Optional[str], optional): Base64 encoded date string. Defaults to None.
            first (Optional[int], optional): Number of records to fetch. If None, will be calculated based on the month.
            
        Returns:
            Dict[str, Any]: The consumption data from the API
        """
        # If first is not provided, calculate it based on the after_date
        if first is None and after_date:
            # If after_date is Base64 encoded, decode it first
            if after_date.startswith('MjAy') or re.match(r'^[A-Za-z0-9+/=]+$', after_date):
                try:
                    decoded_date = base64.b64decode(after_date).decode('utf-8')
                    first = calculate_first_parameter(decoded_date)
                except Exception as e:
                    logger.warning(f"Failed to decode Base64 date, using default first value: {e}")
                    first = 720
            else:
                first = calculate_first_parameter(after_date)
            logger.info(f"Calculated 'first' parameter: {first} hours")
        
        # Use default if still None
        if first is None:
            first = 720
            logger.info(f"Using default 'first' parameter: {first} hours")
        
        query = """
        {
          viewer {
            homes {
              consumption(resolution: HOURLY, after: "%s", first: %d) {
                nodes {
                  from
                  to
                  consumption
                  consumptionUnit
                }
              }
            }
          }
        }
        """ % (after_date or "MjAyNC0wNi0wMVQwMDowMDowMCswMjowMA==", first)
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={"query": query}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching consumption data: {e}")
            raise

def fetch_and_save_consumption(
    access_token: str,
    output_file: str,
    after_date: Optional[str] = None,
    first: Optional[int] = None
) -> None:
    """
    Fetch consumption data from Tibber API and save it to a JSON file.
    
    Args:
        access_token (str): The Tibber API access token
        output_file (str): Path to save the JSON file
        after_date (Optional[str], optional): Base64 encoded date string. Defaults to None.
        first (Optional[int], optional): Number of records to fetch. If None, will be calculated based on the month.
    """
    # Initialize API client
    api = TibberAPI(access_token)
    
    try:
        # Fetch consumption data
        data = api.get_consumption_data(after_date, first)
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Successfully saved consumption data to {output_file}")
        
    except Exception as e:
        logger.error(f"Error in fetch_and_save_consumption: {e}")
        raise

def parse_date_range(date_range: str) -> tuple[datetime, datetime]:
    """
    Parse a date range string in format "YYYY-MM; YYYY-MM" into start and end datetime objects.
    
    Args:
        date_range (str): Date range string in format "YYYY-MM; YYYY-MM"
        
    Returns:
        tuple[datetime, datetime]: Start and end datetime objects
        
    Raises:
        ValueError: If the date range format is invalid or end date is before start date
    """
    try:
        # Split the range into start and end dates
        start_str, end_str = [d.strip() for d in date_range.split(';')]
        
        # Parse the dates
        start_date = datetime.strptime(start_str, '%Y-%m')
        end_date = datetime.strptime(end_str, '%Y-%m')
        
        # Validate the date range
        if end_date < start_date:
            raise ValueError(f"End date {end_str} is before start date {start_str}")
            
        # Check if end date is not in the future
        current_date = datetime.now()
        if end_date > current_date:
            raise ValueError(f"End date {end_str} is in the future")
            
        return start_date, end_date
    except ValueError as e:
        logger.error(f"Error parsing date range: {e}")
        raise

def generate_month_range(start_date: datetime, end_date: datetime) -> list[str]:
    """
    Generate a list of year-month strings between start_date and end_date (inclusive).
    
    Args:
        start_date (datetime): Start date
        end_date (datetime): End date
        
    Returns:
        list[str]: List of year-month strings in format "YYYY-MM"
    """
    current_date = start_date
    month_range = []
    
    while current_date <= end_date:
        month_range.append(current_date.strftime('%Y-%m'))
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
            
    return month_range

def process_date_range(access_token: str, date_range: str, first: Optional[int] = None) -> None:
    """
    Process a date range by fetching and saving consumption data for each month.
    
    Args:
        access_token (str): Tibber API access token
        date_range (str): Date range in format "YYYY-MM; YYYY-MM"
        first (Optional[int]): Number of records to fetch per request
    """
    try:
        start_date, end_date = parse_date_range(date_range)
        months = generate_month_range(start_date, end_date)
        
        for month in months:
            try:
                encoded_date = encode_date_to_base64(month)
                output_file = f"data/input/{month}-Verbrauch.json"
                fetch_and_save_consumption(access_token, output_file, encoded_date, first)
            except Exception as e:
                logger.error(f"Error processing month {month}: {e}")
                continue
    except Exception as e:
        logger.error(f"Error processing date range: {e}")
        raise

if __name__ == "__main__":
    # Load configuration
    config = load_config()
    
    # Get Tibber API configuration
    tibber_config = config['tibber']
    access_token = tibber_config['access_token']
    
    # Get date range from config
    date_range = tibber_config.get('date_range')
    if not date_range:
        logger.error("No date range specified in config.yaml")
        raise ValueError("date_range is required in config.yaml")
    
    # Process the date range
    process_date_range(
        access_token=access_token,
        date_range=date_range,
        first=tibber_config.get('first')
    ) 