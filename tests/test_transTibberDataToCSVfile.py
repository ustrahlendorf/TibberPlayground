"""
Test cases for the transTibberDataToCSVfile module.
"""
import json
import csv
import yaml
from pathlib import Path
import pytest
from datetime import datetime
from src.transTibberDataToCSVfile import (
    main, 
    transform_consumption_to_csv, 
    load_config, 
    find_json_files, 
    extract_year_month_from_filename
)


@pytest.fixture
def setup_test_environment(tmp_path, monkeypatch):
    """
    Set up test environment with necessary directory structure and files.
    """
    # Create directory structure
    data_dir = tmp_path / "data"
    input_dir = data_dir / "input"
    output_dir = data_dir / "output"
    config_dir = tmp_path / "config"
    
    for directory in [input_dir, output_dir, config_dir]:
        directory.mkdir(parents=True)
    
    # Create sample JSON data
    json_data = {
        "data": {
            "viewer": {
                "homes": [
                    {
                        "consumption": {
                            "nodes": [
                                {
                                    "from": "2024-11-01T00:00:00.000+01:00",
                                    "to": "2024-11-01T01:00:00.000+01:00",
                                    "consumption": 0.56,
                                    "consumptionUnit": "kWh"
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
    
    # Create config file
    config = {
        'paths': {
            'input': {
                'json_file_prefix': '-Verbrauch.json'
            },
            'output': {
                'csv_file_prefix': '-consumption.csv'
            }
        },
        'directories': {
            'data': 'data',
            'input': 'input',
            'output': 'output'
        },
        'csv': {
            'header': ['Datetime', 'Power'],
            'empty_columns': 9,
            'decimal_separator': ',',
            'date_format': '%Y%m%d:%H'
        },
        'processing': {
            'consumption_multiplier': 1000,
            'decimal_places': 2
        },
        'tibber': {
            'access_token': 'test-token'
        }
    }
    
    # Write config file
    config_path = config_dir / "config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    
    # Write multiple JSON files with different month prefixes
    json_files = [
        "2024-11-Verbrauch.json",
        "2024-10-Verbrauch.json",
        "2024-09-Verbrauch.json"
    ]
    
    for json_file in json_files:
        json_file_path = input_dir / json_file
        with open(json_file_path, 'w') as f:
            json.dump(json_data, f)
    
    # Mock the project root directory
    monkeypatch.setattr(Path, "parent", lambda self: tmp_path if str(self).endswith("transTibberDataToCSVfile.py") else self.parent)
    
    return tmp_path


def test_main(capsys, setup_test_environment):
    """
    Test the main function.
    """
    # Run main function with the test environment root
    main(project_root=setup_test_environment)
    
    # Check output
    captured = capsys.readouterr()
    assert "Found 3 JSON files to process" in captured.out
    assert "Processed 3 of 3 files successfully" in captured.out
    
    # Verify output files exist and contain correct data
    for month in ["2024-11", "2024-10", "2024-09"]:
        output_file = setup_test_environment / "data" / "output" / f"{month}-consumption.csv"
        assert output_file.exists()
        
        # Check CSV contents
        with open(output_file, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
            # Check header
            assert rows[0] == ['Datetime', 'Power'] + [''] * 9
            
            # Check data row
            assert rows[1][0] == '20241101:00'  # Formatted datetime
            assert rows[1][1] == '560,00'  # Consumption value (0.56 * 1000)


def test_transform_consumption_to_csv(tmp_path):
    """
    Test the transform_consumption_to_csv function.
    """
    # Create a temporary config file
    config = {
        'csv': {
            'header': ['Datetime', 'Power'],
            'empty_columns': 9,
            'decimal_separator': ',',
            'date_format': '%Y%m%d:%H'
        },
        'processing': {
            'consumption_multiplier': 1000,
            'decimal_places': 2
        }
    }
    
    # Create a temporary JSON file with sample data
    json_data = {
        "data": {
            "viewer": {
                "homes": [
                    {
                        "consumption": {
                            "nodes": [
                                {
                                    "from": "2024-06-01T00:00:00.000+02:00",
                                    "to": "2024-06-01T01:00:00.000+02:00",
                                    "consumption": 0.56,
                                    "consumptionUnit": "kWh"
                                },
                                {
                                    "from": "2024-06-01T01:00:00.000+02:00",
                                    "to": "2024-06-01T02:00:00.000+02:00",
                                    "consumption": 0.281,
                                    "consumptionUnit": "kWh"
                                },
                                {
                                    "from": "2024-06-01T02:00:00.000+02:00",
                                    "to": "2024-06-01T03:00:00.000+02:00",
                                    "consumption": 0.456819,
                                    "consumptionUnit": "kWh"
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
    
    json_file_path = tmp_path / "test_data.json"
    with open(json_file_path, 'w') as f:
        json.dump(json_data, f)
    
    # Define output CSV path
    output_csv_path = tmp_path / "test_output.csv"
    
    # Run the transformation
    result = transform_consumption_to_csv(json_file_path, output_csv_path, config)
    
    # Check if transformation was successful
    assert result is True
    
    # Check if output file exists
    assert output_csv_path.exists()
    
    # Read the CSV file and check its contents
    with open(output_csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    # Check header
    expected_header = config['csv']['header'] + [''] * config['csv']['empty_columns']
    assert rows[0] == expected_header
    
    # Check first data row
    assert rows[1][0] == '20240601:00'  # Formatted datetime
    assert rows[1][1] == '560,00'  # Consumption value (0.56 * 1000)
    
    # Check second data row
    assert rows[2][0] == '20240601:01'  # Formatted datetime
    assert rows[2][1] == '281,00'  # Consumption value (0.281 * 1000)
    
    # Check third data row with rounding
    assert rows[3][0] == '20240601:02'  # Formatted datetime
    assert rows[3][1] == '456,82'  # Consumption value (0.456819 * 1000) rounded to 2 decimal places


def test_load_config(tmp_path):
    """
    Test the load_config function.
    """
    # Create a temporary config file
    config_data = {
        'paths': {
            'input': {
                'json_file_prefix': '-Verbrauch.json'
            },
            'output': {
                'csv_file_prefix': '-consumption.csv'
            }
        },
        'directories': {
            'data': 'data',
            'input': 'input',
            'output': 'output'
        }
    }
    
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config_data, f)
    
    # Load the config
    loaded_config = load_config(config_path)
    
    # Check if config was loaded correctly
    assert loaded_config == config_data


def test_find_json_files(tmp_path):
    """
    Test the find_json_files function.
    """
    # Create input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # Create multiple JSON files with different prefixes
    json_files = [
        "2024-11-Verbrauch.json",
        "2024-10-Verbrauch.json",
        "2024-09-Verbrauch.json",
        "2024-08-other.json"  # This one should not be included
    ]
    
    for json_file in json_files:
        with open(input_dir / json_file, 'w') as f:
            f.write("{}")
    
    # Test finding files with the correct prefix
    json_file_prefix = "-Verbrauch.json"
    found_files = find_json_files(input_dir, json_file_prefix)
    
    # Check that only files with the correct prefix were found
    assert len(found_files) == 3
    assert all(file.name.endswith("-Verbrauch.json") for file in found_files)
    
    # Test with a prefix that doesn't match any files
    found_files = find_json_files(input_dir, "-nonexistent.json")
    assert len(found_files) == 0


def test_extract_year_month_from_filename(tmp_path):
    """
    Test the extract_year_month_from_filename function.
    """
    # Create test files with different naming patterns
    test_files = [
        "2024-11-Verbrauch.json",
        "2023-01-other.json",
        "invalid-name.json"
    ]
    
    for file_name in test_files:
        file_path = tmp_path / file_name
        with open(file_path, 'w') as f:
            f.write("{}")
    
    # Test valid filenames
    year_month = extract_year_month_from_filename(tmp_path / "2024-11-Verbrauch.json")
    assert year_month == "2024-11"
    
    year_month = extract_year_month_from_filename(tmp_path / "2023-01-other.json")
    assert year_month == "2023-01"
    
    # Test invalid filename
    year_month = extract_year_month_from_filename(tmp_path / "invalid-name.json")
    assert year_month is None 