import pytest
from pathlib import Path
from datetime import datetime, timedelta
import csv
import tempfile
import os
from src.validateCSVfile import CSVValidator

@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        yield f
    os.unlink(f.name)

@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    return {
        'csv': {
            'delimiter': ',',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'decimal_separator': ',',
            'header': ['timestamp', 'power']
        },
        'directories': {
            'data': 'data',
            'output': 'output'
        },
        'paths': {
            'output': {
                'csv_file_prefix': '.csv'
            }
        }
    }

@pytest.fixture
def validator(sample_config, tmp_path):
    """Create a validator instance with a temporary config file."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f)
    
    return CSVValidator(str(config_file))

def create_test_csv(file_path, rows):
    """Helper function to create a test CSV file."""
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'power'])
        writer.writerows(rows)

def test_valid_continuous_data(validator, temp_csv_file):
    """Test validation of a valid CSV file with continuous data."""
    # Create 48 hours of continuous data
    base_time = datetime(2024, 3, 1, 0, 0, 0)
    rows = []
    for i in range(48):
        timestamp = base_time + timedelta(hours=i)
        rows.append([timestamp.strftime('%Y-%m-%d %H:%M:%S'), '100,5'])
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert is_valid
    assert len(errors) == 0

def test_duplicate_timestamp(validator, temp_csv_file):
    """Test detection of duplicate timestamps."""
    base_time = datetime(2024, 3, 1, 0, 0, 0)
    rows = [
        [base_time.strftime('%Y-%m-%d %H:%M:%S'), '100,5'],
        [base_time.strftime('%Y-%m-%d %H:%M:%S'), '200,5'],  # Duplicate timestamp
        [(base_time + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'), '150,5']
    ]
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    assert any('Duplicate timestamp found' in error and 'also found at row' in error for error in errors)
    # Print errors for debugging
    print(f"Errors: {errors}")

def test_missing_hours(validator, temp_csv_file):
    """Test detection of missing hours in a day."""
    base_time = datetime(2024, 3, 1, 0, 0, 0)
    rows = []
    # Create data for hours 0, 1, 2, 4 (missing hour 3)
    for hour in [0, 1, 2, 4]:
        timestamp = base_time + timedelta(hours=hour)
        rows.append([timestamp.strftime('%Y-%m-%d %H:%M:%S'), '100,5'])
    
    # Add a second day with all hours to ensure the validator checks all days
    second_day = base_time + timedelta(days=1)
    for hour in range(24):
        timestamp = second_day + timedelta(hours=hour)
        rows.append([timestamp.strftime('%Y-%m-%d %H:%M:%S'), '100,5'])
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    # Print errors for debugging
    print(f"Errors: {errors}")
    # Check for any error message about missing hours
    assert any('Missing hours' in error and '3' in error and 'between rows' in error for error in errors)

def test_date_gap(validator, temp_csv_file):
    """Test detection of gaps between dates."""
    base_time = datetime(2024, 3, 1, 0, 0, 0)
    rows = []
    # Create data for March 1st and March 3rd (missing March 2nd)
    for day in [0, 2]:  # 0 = March 1, 2 = March 3
        for hour in range(24):
            timestamp = base_time + timedelta(days=day, hours=hour)
            rows.append([timestamp.strftime('%Y-%m-%d %H:%M:%S'), '100,5'])
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    assert any('Gap in dates between' in error and 'between rows' in error for error in errors)
    # Print errors for debugging
    print(f"Errors: {errors}")

def test_invalid_datetime_format(validator, temp_csv_file):
    """Test detection of invalid datetime format."""
    rows = [
        ['2024-03-01 00:00:00', '100,5'],
        ['invalid-date', '200,5'],
        ['2024-03-01 02:00:00', '150,5']
    ]
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    assert any('Invalid datetime format' in error for error in errors)

def test_invalid_power_value(validator, temp_csv_file):
    """Test detection of invalid power values."""
    base_time = datetime(2024, 3, 1, 0, 0, 0)
    rows = [
        [base_time.strftime('%Y-%m-%d %H:%M:%S'), '100,5'],
        [(base_time + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'), 'invalid'],
        [(base_time + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'), '150,5']
    ]
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    assert any('Invalid power value' in error for error in errors)

def test_empty_file(validator, temp_csv_file):
    """Test validation of an empty file."""
    # Create a file with just the header
    with open(temp_csv_file.name, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'power'])
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    assert any('File contains only a header row' in error for error in errors)
    # Print errors for debugging
    print(f"Errors: {errors}")

def test_multiple_validation_issues(validator, temp_csv_file):
    """Test detection of multiple validation issues in the same file."""
    base_time = datetime(2024, 3, 1, 0, 0, 0)
    rows = [
        [base_time.strftime('%Y-%m-%d %H:%M:%S'), '100,5'],
        [base_time.strftime('%Y-%m-%d %H:%M:%S'), '200,5'],  # Duplicate
        ['invalid-date', '150,5'],  # Invalid date
        [(base_time + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S'), 'invalid']  # Invalid power
    ]
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    assert len(errors) >= 4  # Should catch all issues

def test_missing_hour_in_middle_of_day(validator, temp_csv_file):
    """Test detection of missing hours in the middle of a day (like hour 2 on March 30, 2025)."""
    base_time = datetime(2025, 3, 30, 0, 0, 0)
    rows = []
    
    # Create data for March 30, 2025 with hour 2 missing
    for hour in [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]:
        timestamp = base_time + timedelta(hours=hour)
        rows.append([timestamp.strftime('%Y-%m-%d %H:%M:%S'), '100,5'])
    
    create_test_csv(temp_csv_file.name, rows)
    
    is_valid, errors = validator.validate_file_content(Path(temp_csv_file.name))
    assert not is_valid
    # Print errors for debugging
    print(f"Errors: {errors}")
    # Check for any error message about missing hours
    assert any('Missing hours' in error and '2' in error and 'between rows' in error for error in errors) 