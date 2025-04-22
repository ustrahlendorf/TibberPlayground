# TibberAPI Data Processing

A Python application for transforming Tibber consumption data from JSON to CSV format.

## Features

- Converts Tibber API JSON data to CSV format
- Configurable output format through YAML configuration
- Supports batch processing of multiple files
- Handles date formatting and decimal separator
- Automated testing with pytest
- Type checking with mypy
- Code formatting with black
- Code linting with flake8

## Requirements

- Python 3.8 or higher
- PyYAML
- Required packages listed in requirements.txt

## Project Structure

```bash
.
├── src/                # Source code for the application
│   └── transTibberDataToCSVfile.py  # Main processing script
├── tests/             # Test files and test resources
├── data/              # Data directory
│   ├── input/         # Input JSON files from Tibber API
│   └── output/        # Generated CSV files
├── config/            # Configuration files
│   └── config.yaml    # Main configuration file
├── requirements.txt   # Project dependencies
├── setup.py          # Package setup configuration
├── pytest.ini        # Pytest configuration
├── README.md         # Project documentation
└── .gitignore        # Git ignore file
```

## Setup

### Environment Setup

1. Clone the repository:
```bash
git clone [your-repository-url]
cd GetVerbrauch
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install the package in development mode:
```bash
pip install -e .
```

### Configuration

1. Navigate to the `config` directory
2. Copy or modify `config.yaml` with your preferences:
   - Configure input/output directories
   - Set date formats
   - Adjust decimal separators
   - Configure CSV output format

## Usage

### Basic Usage

Run the main script:
```bash
python src/transTibberDataToCSVfile.py
```

### Data Directory Structure

- Place your Tibber API JSON files in `data/input/`
- Processed CSV files will be generated in `data/output/`
- File naming convention: `YYYY-MM-[prefix].json` → `YYYY-MM-consumption.csv`

## Development

### Code Quality Tools

The project uses several tools to maintain code quality:

- **pytest**: For running tests
  ```bash
  python -m pytest tests/
  ```

- **black**: For code formatting
  ```bash
  black src/ tests/
  ```

- **flake8**: For code linting
  ```bash
  flake8 src/ tests/
  ```

- **mypy**: For type checking
  ```bash
  mypy src/
  ```

### Running Tests

Run the full test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src tests/
```

### Development Best Practices

1. Always activate virtual environment before development
2. Update requirements.txt when adding new dependencies:
   ```bash
   pip freeze > requirements.txt
   ```
3. Run all code quality tools before committing
4. Write tests for new features

## Configuration File

The `config.yaml` file supports the following settings:

```yaml
directories:
  data: data
  input: input
  output: output

paths:
  input:
    json_file_prefix: "-consumption-data.json"
  output:
    csv_file_prefix: "-consumption.csv"

csv:
  header: ["timestamp", "consumption"]
  date_format: "%Y-%m-%d %H:%M:%S"
  decimal_separator: "."
  empty_columns: 0

processing:
  consumption_multiplier: 1.0
  decimal_places: 3
```

## Troubleshooting

Common issues and solutions:

1. **File Not Found Errors**: Ensure proper directory structure in `data/`
2. **Import Errors**: Verify virtual environment is activated
3. **Configuration Errors**: Check `config.yaml` format and values

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality tools
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
