import pytest
from unittest.mock import Mock, patch, mock_open, call
import json
from datetime import datetime, timedelta
import os
import yaml
import base64
from unittest import mock
from src.getTibberData import TibberAPI, fetch_and_save_consumption, load_config, encode_date_to_base64, extract_year_month, calculate_first_parameter, is_german_summer_time, get_german_timezone_offset, parse_date_range, generate_month_range, process_date_range

# Sample test data
SAMPLE_CONFIG = {
    'tibber': {
        'access_token': 'test-token',
        'after_date': 'test-date',
        'first': 720
    },
    'directories': {
        'data': 'data',
        'input': 'input'
    },
    'paths': {
        'input': {
            'json_file_prefix': 'test.json'
        }
    }
}

SAMPLE_API_RESPONSE = {
    'data': {
        'viewer': {
            'homes': [{
                'consumption': {
                    'nodes': [
                        {
                            'from': '2024-06-01T00:00:00+02:00',
                            'to': '2024-06-01T01:00:00+02:00',
                            'consumption': 1.5,
                            'consumptionUnit': 'kWh'
                        }
                    ]
                }
            }]
        }
    }
}

@pytest.fixture
def mock_config():
    """Fixture to mock the config loading."""
    with patch('src.getTibberData.load_config', return_value=SAMPLE_CONFIG):
        yield SAMPLE_CONFIG

@pytest.fixture
def mock_response():
    """Fixture to create a mock response object."""
    mock = Mock()
    mock.json.return_value = SAMPLE_API_RESPONSE
    mock.raise_for_status = Mock()
    return mock

@pytest.fixture
def tibber_api():
    """Fixture to create a TibberAPI instance."""
    return TibberAPI('test-token')

class TestTibberAPI:
    """Test cases for the TibberAPI class."""
    
    def test_init(self):
        """Test initialization of TibberAPI class."""
        api = TibberAPI('test-token')
        assert api.access_token == 'test-token'
        assert api.base_url == 'https://api.tibber.com/v1-beta/gql'
        assert api.headers == {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
        }
    
    @patch('requests.post')
    def test_get_consumption_data_success(self, mock_post, tibber_api, mock_response):
        """Test successful consumption data retrieval."""
        mock_post.return_value = mock_response
        
        result = tibber_api.get_consumption_data()
        
        assert result == SAMPLE_API_RESPONSE
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert 'query' in call_args['json']
        assert 'Bearer test-token' in call_args['headers']['Authorization']
    
    @patch('requests.post')
    def test_get_consumption_data_with_custom_params(self, mock_post, tibber_api, mock_response):
        """Test consumption data retrieval with custom parameters."""
        mock_post.return_value = mock_response
        
        result = tibber_api.get_consumption_data(after_date='custom-date', first=100)
        
        assert result == SAMPLE_API_RESPONSE
        call_args = mock_post.call_args[1]
        assert 'custom-date' in call_args['json']['query']
        assert 'first: 100' in call_args['json']['query']
    
    @patch('requests.post')
    def test_get_consumption_data_error(self, mock_post, tibber_api):
        """Test error handling in consumption data retrieval."""
        mock_post.side_effect = Exception('API Error')
        
        with pytest.raises(Exception) as exc_info:
            tibber_api.get_consumption_data()
        
        assert str(exc_info.value) == 'API Error'

class TestExtractYearMonth:
    """Test cases for the extract_year_month function."""
    
    def test_extract_from_iso8601(self):
        """Test extracting year-month from ISO8601 date string."""
        date_str = "2024-06-01T00:00:00+02:00"
        result = extract_year_month(date_str)
        assert result == "2024-06"
    
    def test_extract_from_date_only(self):
        """Test extracting year-month from date-only string."""
        date_str = "2024-06-01"
        result = extract_year_month(date_str)
        assert result == "2024-06"
    
    def test_extract_from_year_month(self):
        """Test extracting year-month from year-month string."""
        date_str = "2024-06"
        result = extract_year_month(date_str)
        assert result == "2024-06"
    
    def test_extract_from_base64(self):
        """Test extracting year-month from Base64 encoded date string."""
        date_str = "2024-06-01T00:00:00+02:00"
        encoded = base64.b64encode(date_str.encode('utf-8')).decode('utf-8')
        result = extract_year_month(encoded)
        assert result == "2024-06"
    
    def test_extract_invalid_date(self):
        """Test extracting year-month from invalid date string."""
        with pytest.raises(ValueError):
            extract_year_month("invalid-date")

class TestFetchAndSaveConsumption:
    """Test cases for the fetch_and_save_consumption function."""
    
    @patch('src.getTibberData.TibberAPI')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('src.getTibberData.extract_year_month')
    def test_fetch_and_save_success(self, mock_extract, mock_makedirs, mock_file, mock_api_class, mock_config):
        """Test successful fetch and save operation."""
        # Setup mock API
        mock_api_instance = Mock()
        mock_api_instance.get_consumption_data.return_value = SAMPLE_API_RESPONSE
        mock_api_class.return_value = mock_api_instance
        
        # Setup mock extract_year_month
        mock_extract.return_value = "2024-06"
        
        # Call function
        fetch_and_save_consumption(
            access_token='test-token',
            output_file='test/2024-06-test.json',
            after_date='test-date',
            first=720
        )
        
        # Verify API was called
        mock_api_instance.get_consumption_data.assert_called_once_with('test-date', 720)
        
        # Verify file operations
        mock_makedirs.assert_called_once_with('test', exist_ok=True)
        mock_file.assert_called_once_with('test/2024-06-test.json', 'w', encoding='utf-8')
        
        # Get the written data and verify it matches the expected JSON
        written_data = ''.join(call.args[0] for call in mock_file().write.call_args_list)
        assert json.loads(written_data) == SAMPLE_API_RESPONSE
    
    @patch('src.getTibberData.TibberAPI')
    def test_fetch_and_save_api_error(self, mock_api_class, mock_config):
        """Test error handling when API call fails."""
        # Setup mock API to raise an exception
        mock_api_instance = Mock()
        mock_api_instance.get_consumption_data.side_effect = Exception('API Error')
        mock_api_class.return_value = mock_api_instance
        
        # Verify function raises the exception
        with pytest.raises(Exception) as exc_info:
            fetch_and_save_consumption(
                access_token='test-token',
                output_file='test/output.json'
            )
        
        assert str(exc_info.value) == 'API Error'

class TestLoadConfig:
    """Test cases for the load_config function."""
    
    @patch('builtins.open', new_callable=mock_open, read_data=yaml.dump(SAMPLE_CONFIG))
    def test_load_config_success(self, mock_file):
        """Test successful config loading."""
        config = load_config()
        assert config == SAMPLE_CONFIG
    
    @patch('builtins.open')
    def test_load_config_file_not_found(self, mock_file):
        """Test error handling when config file is not found."""
        mock_file.side_effect = FileNotFoundError()
        
        with pytest.raises(FileNotFoundError):
            load_config()
    
    @patch('builtins.open', new_callable=mock_open, read_data='invalid: yaml: [')
    def test_load_config_invalid_yaml(self, mock_file):
        """Test error handling when config file contains invalid YAML."""
        with pytest.raises(yaml.YAMLError):
            load_config()

class TestEncodeDateToBase64:
    """Test cases for the encode_date_to_base64 function."""
    
    def test_encode_date_with_timezone(self):
        """Test encoding a date with timezone."""
        date_str = "2024-06-01T00:00:00.000+02:00"
        expected = base64.b64encode(date_str.encode('utf-8')).decode('utf-8')
        result = encode_date_to_base64(date_str)
        assert result == expected
    
    def test_encode_date_without_timezone(self):
        """Test encoding a date without timezone (should add German timezone)."""
        date_str = "2024-06-01T00:00:00.000"
        # June is during summer time, so it should add +02:00
        expected = base64.b64encode((date_str + "+02:00").encode('utf-8')).decode('utf-8')
        result = encode_date_to_base64(date_str)
        assert result == expected
    
    def test_encode_date_with_z_timezone(self):
        """Test encoding a date with Z timezone."""
        date_str = "2024-06-01T00:00:00.000Z"
        expected = base64.b64encode(date_str.encode('utf-8')).decode('utf-8')
        result = encode_date_to_base64(date_str)
        assert result == expected
    
    def test_encode_date_only(self):
        """Test encoding a date-only string (should add time and German timezone)."""
        date_str = "2024-06-01"
        # June is during summer time, so it should add +02:00
        expected = base64.b64encode("2024-06-01T00:00:00.000+02:00".encode('utf-8')).decode('utf-8')
        result = encode_date_to_base64(date_str)
        assert result == expected
    
    def test_encode_year_month_only(self):
        """Test encoding a year-month string (should add day, time and German timezone)."""
        date_str = "2024-05"
        # May is during summer time, so it should add +02:00
        expected = base64.b64encode("2024-05-01T00:00:00.000+02:00".encode('utf-8')).decode('utf-8')
        result = encode_date_to_base64(date_str)
        assert result == expected
    
    def test_encode_invalid_date(self):
        """Test encoding an invalid date."""
        with pytest.raises(Exception):
            encode_date_to_base64("invalid-date")
    
    def test_encode_date_without_milliseconds(self):
        """Test encoding a date without milliseconds (should add milliseconds)."""
        date_str = "2024-06-01T00:00:00+02:00"
        expected = base64.b64encode("2024-06-01T00:00:00.000+02:00".encode('utf-8')).decode('utf-8')
        result = encode_date_to_base64(date_str)
        assert result == expected

class TestCalculateFirstParameter:
    def test_calculate_first_parameter(self):
        # Test for a month with 30 days
        assert calculate_first_parameter('2024-06') == 720  # 30 days * 24 hours
        
        # Test for a month with 31 days
        assert calculate_first_parameter('2024-07') == 744  # 31 days * 24 hours (capped at 744)
        
        # Test for February in a leap year
        assert calculate_first_parameter('2024-02') == 696  # 29 days * 24 hours
        
        # Test for February in a non-leap year
        assert calculate_first_parameter('2023-02') == 672  # 28 days * 24 hours
        
        # Test with invalid date format
        assert calculate_first_parameter('invalid-date') == 720  # Default value

class TestGermanTimezone:
    def test_is_german_summer_time(self):
        # Test during summer time (DST)
        summer_date = datetime(2024, 6, 1, 12, 0)  # June 1, 2024 (during DST)
        assert is_german_summer_time(summer_date) is True
        
        # Test during winter time (standard)
        winter_date = datetime(2024, 1, 1, 12, 0)  # January 1, 2024 (not during DST)
        assert is_german_summer_time(winter_date) is False
        
        # Test during transition to summer time
        transition_to_summer = datetime(2024, 3, 31, 2, 0)  # March 31, 2024 (transition to DST)
        assert is_german_summer_time(transition_to_summer) is True
        
        # Test during transition to winter time
        # Use a date that's definitely after the DST transition (October 27, 2024 is the last Sunday in October)
        # The transition happens at 3:00 AM, so 4:00 AM should definitely be in standard time
        transition_to_winter = datetime(2024, 10, 27, 4, 0)  # October 27, 2024, 4:00 AM (after transition from DST)
        assert is_german_summer_time(transition_to_winter) is False

    def test_get_german_timezone_offset(self):
        # Test during summer time (DST)
        summer_date = datetime(2024, 6, 1, 12, 0)  # June 1, 2024 (during DST)
        assert get_german_timezone_offset(summer_date) == '+02:00'
        
        # Test during winter time (standard)
        winter_date = datetime(2024, 1, 1, 12, 0)  # January 1, 2024 (not during DST)
        assert get_german_timezone_offset(winter_date) == '+01:00' 

class TestParseDateRange:
    """Test cases for the parse_date_range function."""
    
    def test_parse_valid_date_range(self):
        """Test parsing a valid date range string."""
        date_range = "2024-01; 2024-06"
        start_date, end_date = parse_date_range(date_range)
        
        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        assert start_date.year == 2024
        assert start_date.month == 1
        assert end_date.year == 2024
        assert end_date.month == 6
    
    def test_parse_date_range_with_whitespace(self):
        """Test parsing a date range string with extra whitespace."""
        date_range = "  2024-01  ;  2024-06  "
        start_date, end_date = parse_date_range(date_range)
        
        assert start_date.year == 2024
        assert start_date.month == 1
        assert end_date.year == 2024
        assert end_date.month == 6
    
    def test_parse_invalid_date_range_format(self):
        """Test parsing an invalid date range format."""
        with pytest.raises(ValueError):
            parse_date_range("2024-01-2024-06")
    
    def test_parse_invalid_date_format(self):
        """Test parsing an invalid date format."""
        with pytest.raises(ValueError):
            parse_date_range("2024/01; 2024/06")
    
    def test_parse_end_date_before_start_date(self):
        """Test parsing a date range where end date is before start date."""
        with pytest.raises(ValueError):
            parse_date_range("2024-06; 2024-01")
    
    def test_parse_future_end_date(self):
        """Test parsing a date range where end date is in the future."""
        future_date = (datetime.now().replace(day=1) + timedelta(days=32)).strftime("%Y-%m")
        current_date = datetime.now().strftime("%Y-%m")
        with pytest.raises(ValueError):
            parse_date_range(f"{current_date}; {future_date}")

class TestGenerateMonthRange:
    """Test cases for the generate_month_range function."""
    
    def test_generate_month_range_same_month(self):
        """Test generating month range for the same month."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        result = generate_month_range(start_date, end_date)
        
        assert result == ["2024-01"]
    
    def test_generate_month_range_multiple_months(self):
        """Test generating month range for multiple months."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 3, 31)
        result = generate_month_range(start_date, end_date)
        
        assert result == ["2024-01", "2024-02", "2024-03"]
    
    def test_generate_month_range_cross_year(self):
        """Test generating month range across year boundary."""
        start_date = datetime(2024, 12, 1)
        end_date = datetime(2025, 2, 28)
        result = generate_month_range(start_date, end_date)
        
        assert result == ["2024-12", "2025-01", "2025-02"]
    
    def test_generate_month_range_single_day(self):
        """Test generating month range for a single day."""
        date = datetime(2024, 6, 15)
        result = generate_month_range(date, date)
        
        assert result == ["2024-06"]

class TestProcessDateRange:
    """Test cases for the process_date_range function."""
    
    @patch('src.getTibberData.fetch_and_save_consumption')
    @patch('src.getTibberData.encode_date_to_base64')
    @patch('src.getTibberData.parse_date_range')
    @patch('src.getTibberData.generate_month_range')
    def test_process_date_range_success(self, mock_generate_range, mock_parse_range, mock_encode, mock_fetch_and_save):
        """Test successful processing of a date range."""
        date_range = "2024-01; 2024-03"
        access_token = "test-token"
        
        # Setup mocks
        mock_parse_range.return_value = (datetime(2024, 1, 1), datetime(2024, 3, 31))
        mock_generate_range.return_value = ["2024-01", "2024-02", "2024-03"]
        mock_encode.side_effect = lambda x: f"encoded_{x}"
        
        process_date_range(access_token, date_range)
        
        # Verify mocks were called correctly
        mock_parse_range.assert_called_once_with(date_range)
        mock_generate_range.assert_called_once()
        assert mock_encode.call_count == 3
        assert mock_fetch_and_save.call_count == 3
        
        # Verify the calls to fetch_and_save_consumption
        expected_calls = [
            call(access_token, "data/input/2024-01-Verbrauch.json", "encoded_2024-01", None),
            call(access_token, "data/input/2024-02-Verbrauch.json", "encoded_2024-02", None),
            call(access_token, "data/input/2024-03-Verbrauch.json", "encoded_2024-03", None)
        ]
        mock_fetch_and_save.assert_has_calls(expected_calls)
    
    @patch('src.getTibberData.fetch_and_save_consumption')
    @patch('src.getTibberData.encode_date_to_base64')
    @patch('src.getTibberData.parse_date_range')
    @patch('src.getTibberData.generate_month_range')
    def test_process_date_range_with_first_parameter(self, mock_generate_range, mock_parse_range, mock_encode, mock_fetch_and_save):
        """Test processing date range with first parameter specified."""
        date_range = "2024-01; 2024-02"
        access_token = "test-token"
        first = 744
        
        # Setup mocks
        mock_parse_range.return_value = (datetime(2024, 1, 1), datetime(2024, 2, 29))
        mock_generate_range.return_value = ["2024-01", "2024-02"]
        mock_encode.side_effect = lambda x: f"encoded_{x}"
        
        process_date_range(access_token, date_range, first)
        
        # Verify mocks were called correctly
        mock_parse_range.assert_called_once_with(date_range)
        mock_generate_range.assert_called_once()
        assert mock_encode.call_count == 2
        assert mock_fetch_and_save.call_count == 2
        
        # Verify the calls to fetch_and_save_consumption
        expected_calls = [
            call(access_token, "data/input/2024-01-Verbrauch.json", "encoded_2024-01", 744),
            call(access_token, "data/input/2024-02-Verbrauch.json", "encoded_2024-02", 744)
        ]
        mock_fetch_and_save.assert_has_calls(expected_calls)
    
    @patch('src.getTibberData.fetch_and_save_consumption')
    @patch('src.getTibberData.encode_date_to_base64')
    @patch('src.getTibberData.parse_date_range')
    @patch('src.getTibberData.generate_month_range')
    def test_process_date_range_handles_errors(self, mock_generate_range, mock_parse_range, mock_encode, mock_fetch_and_save):
        """Test error handling during date range processing."""
        date_range = "2024-01; 2024-03"
        access_token = "test-token"
        
        # Setup mocks
        mock_parse_range.return_value = (datetime(2024, 1, 1), datetime(2024, 3, 31))
        mock_generate_range.return_value = ["2024-01", "2024-02", "2024-03"]
        mock_encode.side_effect = lambda x: f"encoded_{x}"
        mock_fetch_and_save.side_effect = [None, Exception("API Error"), None]
        
        process_date_range(access_token, date_range)
        
        # Verify all months were attempted
        assert mock_fetch_and_save.call_count == 3 