import pytest
import os
import json
from src.getTibberData import TibberAPI, load_config

@pytest.fixture
def config():
    """Load the actual config file."""
    return load_config()

@pytest.fixture
def tibber_api(config):
    """Create a TibberAPI instance with the actual access token."""
    return TibberAPI(config['tibber']['access_token'])

@pytest.mark.integration
class TestTibberAPIIntegration:
    """Integration tests for TibberAPI that make actual API calls."""

    def test_access_token_validity(self, tibber_api):
        """
        Test that the access token is valid by making a simple query to the API.
        This test verifies that:
        1. The API endpoint is accessible
        2. The access token is valid
        3. The response format is correct
        """
        try:
            # Make the API call using the post method directly
            response = tibber_api.get_consumption_data(first=1)  # Just get one record to verify access
            
            # Verify the response structure
            assert 'data' in response
            assert 'viewer' in response['data']
            assert 'homes' in response['data']['viewer']
            
            # Get basic information
            homes = response['data']['viewer']['homes']
            assert len(homes) > 0
            
            print("\nAPI Connection Test Results:")
            print(f"Access token is valid")
            print(f"Number of homes: {len(homes)}")
            print(f"API endpoint is accessible")
            print(f"Response format is correct")
            
        except Exception as e:
            pytest.fail(f"API connection failed: {str(e)}")
    
    def test_consumption_data_access(self, tibber_api):
        """
        Test that we can access consumption data.
        This test verifies that:
        1. We can query consumption data
        2. The data format is correct
        3. We receive actual consumption values
        """
        try:
            # Make the API call
            response = tibber_api.get_consumption_data(first=24)  # Get 24 data points
            
            # Verify the response structure
            assert 'data' in response
            assert 'viewer' in response['data']
            assert 'homes' in response['data']['viewer']
            
            # Get the consumption nodes
            homes = response['data']['viewer']['homes']
            assert len(homes) > 0
            
            first_home = homes[0]
            assert 'consumption' in first_home
            consumption = first_home['consumption']
            assert 'nodes' in consumption
            
            nodes = consumption['nodes']
            assert len(nodes) > 0
            
            # Verify the structure of consumption data
            first_node = nodes[0]
            assert 'from' in first_node
            assert 'to' in first_node
            assert 'consumption' in first_node
            assert 'consumptionUnit' in first_node
            
            print("\nConsumption Data Test Results:")
            print(f"Successfully retrieved {len(nodes)} consumption data points")
            print(f"Data time range: {nodes[0]['from']} to {nodes[-1]['to']}")
            print(f"Measurement unit: {nodes[0]['consumptionUnit']}")
            print("\nSample consumption values:")
            for node in nodes[:5]:  # Show first 5 entries
                print(f"From {node['from']} to {node['to']}: {node['consumption']} {node['consumptionUnit']}")
            
            # Save sample response to a file for reference
            sample_file = os.path.join('tests', 'sample_response.json')
            with open(sample_file, 'w', encoding='utf-8') as f:
                json.dump(response, f, indent=2)
            print(f"\nSaved sample response to: {sample_file}")
            
        except Exception as e:
            pytest.fail(f"Consumption data access failed: {str(e)}")

if __name__ == '__main__':
    pytest.main(['-v', '-m', 'integration']) 