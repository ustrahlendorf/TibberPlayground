"""
Module to combine all consumption CSV files into a single yearly consumption file.
This program reads all CSV files from the output directory and combines them into
a single file while maintaining chronological order and removing duplicate headers.
"""

import csv
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional


class ConsumptionCSVBuilder:
    """Class to build a total consumption CSV file from individual monthly files."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the CSV builder with configuration.
        
        Args:
            config_path (Optional[str]): Path to the configuration file.
                                       If None, will use default config.yaml in project root.
        """
        self.project_root = self._find_project_root()
        self.config_path = config_path or str(self.project_root / "config" / "config.yaml")
        self.config = self._load_config()
        self.output_dir = self._get_output_dir()
        self.delimiter = self.config['csv'].get('delimiter', ',')
        self.date_format = self.config['csv']['date_format']
        
    def _find_project_root(self) -> Path:
        """
        Find the project root directory by looking for the config directory.
        Searches in the following order:
        1. Script's directory
        2. Parent directories up to 3 levels
        3. Current working directory
        
        Returns:
            Path: The project root directory
            
        Raises:
            FileNotFoundError: If project root cannot be found
        """
        # List of directories to check, in order of preference
        search_paths = [
            Path(__file__).resolve().parent,  # Script's directory
            *[Path(__file__).resolve().parent.parents[i] for i in range(3)],  # Up to 3 parent levels
            Path.cwd()  # Current working directory
        ]
        
        for directory in search_paths:
            if (directory / "config").exists():
                return directory
                
        raise FileNotFoundError(
            "Could not find project root directory. "
            "Please ensure you're running the script from within the project directory "
            "or that the config directory exists in the expected location."
        )
        
    def _get_output_dir(self) -> Path:
        """Get the output directory path from configuration."""
        return self.project_root / self.config['directories']['data'] / self.config['directories']['output']
        
    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in configuration file: {str(e)}")
            
    def get_csv_files(self) -> List[Tuple[Path, datetime]]:
        """
        Get all CSV files from the output directory, sorted by year and month.
        
        Returns:
            List[Tuple[Path, datetime]]: List of tuples containing file paths and their dates
        """
        files = []
        for file_path in self.output_dir.glob(f"*{self.config['paths']['output']['csv_file_prefix']}"):
            # Extract year and month from filename (assuming format: YYYY-MM-consumption.csv)
            try:
                date_str = file_path.stem.split('-')[0:2]  # Get YYYY-MM part
                date = datetime.strptime('-'.join(date_str), '%Y-%m')
                files.append((file_path, date))
            except (ValueError, IndexError):
                print(f"Warning: Could not parse date from filename: {file_path.name}")
                continue
                
        return sorted(files, key=lambda x: x[1])  # Sort by date
        
    def build_total_consumption_csv(self) -> None:
        """Build the total consumption CSV file from all individual files."""
        output_file = self.output_dir / "year-consumption.csv"
        csv_files = self.get_csv_files()
        
        if not csv_files:
            print("No CSV files found to combine.")
            return
            
        with open(output_file, 'w', newline='') as outfile:
            writer = csv.writer(outfile, delimiter=self.delimiter)
            
            # Write header from first file
            with open(csv_files[0][0], 'r') as first_file:
                reader = csv.reader(first_file, delimiter=self.delimiter)
                header = next(reader)
                writer.writerow(header)
            
            # Process each file
            for file_path, _ in csv_files:
                with open(file_path, 'r') as infile:
                    reader = csv.reader(infile, delimiter=self.delimiter)
                    next(reader)  # Skip header
                    for row in reader:
                        writer.writerow(row)
                        
        print(f"Successfully created combined consumption file: {output_file}")


def main():
    """Main entry point for the program."""
    try:
        builder = ConsumptionCSVBuilder()
        builder.build_total_consumption_csv()
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main()) 