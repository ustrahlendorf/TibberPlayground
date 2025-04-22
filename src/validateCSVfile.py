"""
Validation module for CSV files in the output directory.
This module provides functionality to validate the structure and content of CSV files.
"""

import csv
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class CSVValidator:
    """Class to validate CSV files against configuration requirements."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the validator with configuration.
        
        Args:
            config_path (Optional[str]): Path to the configuration file. If None, will look for config.yaml
                                       in the project root directory.
        """
        self.project_root = self._find_project_root()
        self.config_path = config_path or str(self.project_root / "config" / "config.yaml")
        self.config = self._load_config(self.config_path)
        self.output_dir = self._get_output_dir()
        # Set default delimiter to comma if not specified in config
        self.delimiter = self.config.get('csv', {}).get('delimiter', ',')
        # Get required headers from config
        self.required_headers = self.config['csv']['header']
        
    def _find_project_root(self) -> Path:
        """
        Find the project root directory by looking for the config directory.
        
        Returns:
            Path: Path to the project root directory
            
        Raises:
            FileNotFoundError: If project root cannot be found
        """
        current_dir = Path(__file__).resolve().parent
        while current_dir.parent != current_dir:  # Stop at root directory
            if (current_dir / "config").exists():
                return current_dir
            current_dir = current_dir.parent
        raise FileNotFoundError("Could not find project root directory (looking for 'config' directory)")
        
    def _get_output_dir(self) -> Path:
        """
        Get the output directory path from configuration.
        
        Returns:
            Path: Path to the output directory
        """
        return self.project_root / self.config['directories']['data'] / self.config['directories']['output']
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Load configuration from YAML file.
        
        Args:
            config_path (str): Path to the configuration file
            
        Returns:
            Dict: Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file does not exist
            yaml.YAMLError: If config file is invalid YAML
        """
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at: {config_path}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in configuration file: {str(e)}")
            
    def get_csv_files(self) -> List[Path]:
        """
        Get all CSV files from the output directory.
        
        Returns:
            List[Path]: List of paths to CSV files
        """
        return list(self.output_dir.glob(f"*{self.config['paths']['output']['csv_file_prefix']}"))
        
    def validate_file_structure(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate the structure of a CSV file.
        
        Args:
            file_path (Path): Path to the CSV file
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                header = next(reader)
                
                # Validate required headers
                if len(header) < len(self.required_headers):
                    errors.append(f"Header has insufficient columns. Expected at least {len(self.required_headers)} columns.")
                else:
                    # Check if required headers are present and in the correct order
                    for i, required_header in enumerate(self.required_headers):
                        if header[i] != required_header:
                            errors.append(f"Required header '{required_header}' not found at position {i+1}")
                
                # Validate number of columns in data rows
                expected_min_columns = len(self.required_headers)
                for row_num, row in enumerate(reader, start=2):
                    if len(row) < expected_min_columns:
                        errors.append(f"Row {row_num} has insufficient columns. Expected at least {expected_min_columns} columns.")
                        
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
            
        return len(errors) == 0, errors
        
    def validate_file_content(self, file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate the content of a CSV file.
        
        Args:
            file_path (Path): Path to the CSV file
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                next(reader)  # Skip header
                
                # Track seen timestamps and expected sequence
                seen_timestamps = set()
                current_date = None
                expected_hours = set(range(24))
                
                # Check if file has any data rows
                has_data_rows = False
                
                # Track hours for each date
                hours_by_date = {}
                
                # Track line numbers for each timestamp
                timestamp_line_numbers = {}
                
                for row_num, row in enumerate(reader, start=2):
                    if not row:  # Skip empty rows
                        continue
                    
                    has_data_rows = True
                        
                    # Validate datetime format and extract components
                    try:
                        timestamp = datetime.strptime(row[0], self.config['csv']['date_format'])
                        current_hour = timestamp.hour
                        current_date = timestamp.date()
                        
                        # Add timestamp to seen_timestamps set
                        seen_timestamps.add(timestamp)
                        
                        # Track hours for each date
                        if current_date not in hours_by_date:
                            hours_by_date[current_date] = set()
                        hours_by_date[current_date].add(current_hour)
                        
                        # Track line numbers for each timestamp
                        if timestamp in timestamp_line_numbers:
                            timestamp_line_numbers[timestamp].append(row_num)
                        else:
                            timestamp_line_numbers[timestamp] = [row_num]
                        
                        # Check for duplicate timestamps
                        if len(timestamp_line_numbers[timestamp]) > 1:
                            errors.append(f"Row {row_num}: Duplicate timestamp found: {row[0]} (also found at row {timestamp_line_numbers[timestamp][0]})")
                            
                        # Validate power values (should be numeric)
                        try:
                            power_value = row[1].strip('"')  # Remove quotes if present
                            float(power_value.replace(self.config['csv']['decimal_separator'], '.'))
                        except (ValueError, IndexError):
                            errors.append(f"Row {row_num}: Invalid power value in column 2")
                            
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid datetime format in column 1")
                
                # Check if file has any data rows
                if not has_data_rows:
                    errors.append("File contains only a header row. No data rows found.")
                
                # Check for missing hours in each day
                for date, hours in hours_by_date.items():
                    missing_hours = expected_hours - hours
                    if missing_hours:
                        # Find the first and last line numbers for this date
                        date_timestamps = [ts for ts in timestamp_line_numbers.keys() if ts.date() == date]
                        if date_timestamps:
                            first_line = min(timestamp_line_numbers[ts][0] for ts in date_timestamps)
                            last_line = max(timestamp_line_numbers[ts][-1] for ts in date_timestamps)
                            errors.append(f"Missing hours {sorted(missing_hours)} for date {date} (between rows {first_line} and {last_line})")
                        else:
                            errors.append(f"Missing hours {sorted(missing_hours)} for date {date}")
                        
                # Check for gaps between dates
                all_dates = {dt.date() for dt in seen_timestamps}
                if len(all_dates) > 1:
                    sorted_dates = sorted(all_dates)
                    for i in range(len(sorted_dates) - 1):
                        expected_next_date = sorted_dates[i] + timedelta(days=1)
                        if sorted_dates[i + 1] != expected_next_date:
                            # Find the last line of the first date and the first line of the second date
                            first_date_last_line = max(timestamp_line_numbers[ts][-1] for ts in timestamp_line_numbers.keys() if ts.date() == sorted_dates[i])
                            second_date_first_line = min(timestamp_line_numbers[ts][0] for ts in timestamp_line_numbers.keys() if ts.date() == sorted_dates[i + 1])
                            errors.append(f"Gap in dates between {sorted_dates[i]} and {sorted_dates[i + 1]} (between rows {first_date_last_line} and {second_date_first_line})")
                            
        except Exception as e:
            errors.append(f"Error validating content: {str(e)}")
            
        return len(errors) == 0, errors
        
    def validate_all_files(self) -> Dict[Path, Tuple[bool, List[str]]]:
        """
        Validate all CSV files in the output directory.
        
        Returns:
            Dict[Path, Tuple[bool, List[str]]]: Dictionary of file paths and their validation results
        """
        results = {}
        for file_path in self.get_csv_files():
            structure_valid, structure_errors = self.validate_file_structure(file_path)
            content_valid, content_errors = self.validate_file_content(file_path)
            results[file_path] = (structure_valid and content_valid, structure_errors + content_errors)
        return results


def main():
    """Main entry point for the validation program."""
    try:
        validator = CSVValidator()
        results = validator.validate_all_files()
        
        # Print validation results
        for file_path, (is_valid, errors) in results.items():
            print(f"\nValidating {file_path.name}:")
            if is_valid:
                print("✅ File is valid")
            else:
                print("❌ File has validation errors:")
                for error in errors:
                    print(f"  - {error}")
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main()) 