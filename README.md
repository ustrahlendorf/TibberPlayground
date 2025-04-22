# TibberAPI Data Processing

A Python application for transforming Tibber consumption data from JSON to CSV format

## Features

- Converts Tibber API JSON data to CSV format
- Configurable output format through YAML configuration
- Supports batch processing of multiple files
- Handles date formatting and decimal separator

## Requirements

- Python 3.x
- PyYAM

## Setup

1. Clone the repository
2. Install dependencies
3. Configure `config.yaml` with your preferences
4. Run the scrip

## Usage

```python
python src/transTibberDataToCSVfile.py
```

## Project Structure

```bash
.
├── src/               # Source code
├── tests/            # Test files
├── requirements.txt  # Project dependencies
├── README.md        # Project documentation
└── .gitignore       # Git ignore file
```

## Setup-Environment

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Development

- Source code is located in the `src` directory
- Tests are located in the `tests` directory
- Run tests using: `python -m pytest tests/`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
