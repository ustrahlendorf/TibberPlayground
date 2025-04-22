"""
Module for transforming Tibber consumption data from JSON to CSV format.
"""
import json
import csv
from datetime import datetime
import os
from pathlib import Path
import yaml
import glob
import re


def load_config(config_path):
    """
    Load configuration from YAML file.
    
    Args:
        config_path (Path): Path to the configuration file
    
    Returns:
        dict: Configuration dictionary
    """
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def transform_consumption_to_csv(json_file_path, output_csv_path, config):
    """
    Transform consumption data from JSON to CSV format.
    
    Args:
        json_file_path (str): Path to the JSON file containing consumption data
        output_csv_path (str): Path where the CSV file will be saved
        config (dict): Configuration dictionary
    
    Returns:
        bool: True if transformation was successful, False otherwise
    """
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)
        
        # Extract consumption nodes
        consumption_nodes = data['data']['viewer']['homes'][0]['consumption']['nodes']
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_csv_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write to CSV
        with open(output_csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            header = config['csv']['header'] + [''] * config['csv']['empty_columns']
            writer.writerow(header)
            
            # Write data rows
            for node in consumption_nodes:
                # Convert ISO8601 to configured date format
                from_time = datetime.fromisoformat(node['from'].replace('Z', '+00:00'))
                formatted_time = from_time.strftime(config['csv']['date_format'])
                
                # Convert consumption to string with configured decimal separator
                consumption_value = f"{round(node['consumption'] * config['processing']['consumption_multiplier'], config['processing']['decimal_places']):.{config['processing']['decimal_places']}f}".replace('.', config['csv']['decimal_separator'])
                
                # Write row with empty columns
                writer.writerow([formatted_time, consumption_value] + [''] * config['csv']['empty_columns'])
        
        return True
    
    except Exception as e:
        print(f"Error transforming data: {e}")
        return False


def find_json_files(input_dir, json_file_prefix):
    """
    Find all JSON files in the input directory that match the prefix.
    
    Args:
        input_dir (Path): Path to the input directory
        json_file_prefix (str): Prefix of the JSON file to find
    
    Returns:
        list: List of paths to matching JSON files
    """
    # Get all files matching the pattern YYYY-MM{json_file_prefix}
    pattern = str(input_dir / f"*{json_file_prefix}")
    matching_files = glob.glob(pattern)
    
    if not matching_files:
        return []
    
    # Convert to Path objects
    return [Path(file) for file in matching_files]


def extract_year_month_from_filename(file_path):
    """
    Extract year and month from a filename in format YYYY-MM{json_file_prefix}.
    
    Args:
        file_path (Path): Path to the file
    
    Returns:
        str: Year and month in format YYYY-MM, or None if extraction fails
    """
    # Extract the filename without extension
    filename = file_path.stem
    
    # Try to match YYYY-MM pattern
    match = re.match(r'(\d{4}-\d{2})', filename)
    if match:
        return match.group(1)
    
    return None


def main(project_root=None):
    """
    Main entry point for the application.
    
    Args:
        project_root (Path, optional): Project root directory. If None, will be determined automatically.
    """
    # Get the project root directory
    if project_root is None:
        project_root = Path(__file__).parent.parent
    
    # Load configuration
    config_path = project_root / 'config' / 'config.yaml'
    config = load_config(config_path)
    
    # Build directory paths using configuration
    input_dir = project_root / config['directories']['data'] / config['directories']['input']
    output_dir = project_root / config['directories']['data'] / config['directories']['output']
    
    # Find all JSON files in the input directory
    json_file_prefix = config['paths']['input']['json_file_prefix']
    json_files = find_json_files(input_dir, json_file_prefix)
    
    if not json_files:
        print(f"No JSON files found matching pattern *{json_file_prefix} in {input_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    
    # Get the CSV file prefix from config
    csv_file_prefix = config['paths']['output'].get('csv_file_prefix', '-consumption.csv')
    
    # Process each JSON file
    success_count = 0
    for json_file_path in json_files:
        # Extract year-month from the filename
        year_month = extract_year_month_from_filename(json_file_path)
        
        if not year_month:
            print(f"Could not extract year-month from filename: {json_file_path}")
            continue
        
        # Build output CSV path with year-month prefix
        output_csv_path = output_dir / f"{year_month}{csv_file_prefix}"
        
        print(f"Processing file: {json_file_path}")
        print(f"Output file: {output_csv_path}")
        success = transform_consumption_to_csv(json_file_path, output_csv_path, config)
        
        if success:
            print(f"Successfully transformed data to {output_csv_path}")
            success_count += 1
        else:
            print(f"Failed to transform data from {json_file_path}")
    
    print(f"Processed {success_count} of {len(json_files)} files successfully")


if __name__ == "__main__":
    main() 