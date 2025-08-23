"""
Main client class for submitting quantum algorithms to the Qernel resource estimation API.
"""

import logging
import base64
from typing import Dict, Any, Optional
import requests
import cloudpickle

from .exceptions import QernelAPIError
from .config import QernelConfig
from ..algorithm import Algorithm


class QernelClient:
    """Client for submitting quantum algorithms to the Qernel resource estimation API."""
    
    def __init__(self, config: Optional[QernelConfig] = None):
        self.config = config or QernelConfig()
        self.logger = logging.getLogger(__name__)
        
        try:
            self.config.validate()
        except QernelAPIError as e:
            self.logger.warning(f"Configuration validation failed: {e}")
    
    def run_algorithm(self, algorithm_instance: Algorithm) -> Dict[str, Any]:
        """
        Submit an algorithm instance for resource estimation.
        
        Args:
            algorithm_instance: An instance of Algorithm to be executed
            
        Returns:
            Dict containing the API response
            
        Raises:
            QernelAPIError: If the request fails
        """
        # Serialize the algorithm instance using cloudpickle
        serialized_algorithm = cloudpickle.dumps(algorithm_instance)
        
        # Encode as base64 for JSON serialization
        encoded_algorithm = base64.b64encode(serialized_algorithm).decode('utf-8')
        
        # Prepare the request
        url = f"{self.config.api_url}"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.config.api_key
        }
        payload = {'algorithm_pickle': encoded_algorithm}
        
        self.logger.info("Submitting algorithm instance to Qernel API...")
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                result = response.json()
                self.logger.info("Algorithm submitted successfully")
                return result
            else:
                raise QernelAPIError(
                    f"API request failed: {response.status_code} - {response.text}",
                    response.status_code, response.text
                )
                
        except requests.exceptions.RequestException as e:
            raise QernelAPIError(f"Request failed: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the Qernel API."""
        url = f"{self.config.api_url}/"
        headers = {
            'Accept': 'application/json',
            'x-api-key': self.config.api_key
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.config.timeout)
            return {
                'status': 'success' if response.status_code == 200 else 'error',
                'message': 'Connection successful' if response.status_code == 200 else f'Connection failed with status {response.status_code}',
                'response': response.json() if response.status_code == 200 else response.text
            }
        except requests.exceptions.RequestException as e:
            return {'status': 'error', 'message': f'Connection failed: {str(e)}', 'response': None}
        
