"""
Qernel Client Library

Simple client for submitting quantum algorithms to the resource estimation API.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import requests


class QernelClient:
    """Client for submitting quantum algorithms to the resource estimation API."""
    
    def __init__(self, api_url: str = ""):
        """
        Initialize the client.
        
        Args:
            api_url: Base URL for the API
        """
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
    
    def run_algorithm(self, 
                     algorithm_file: str, 
                     spec_file: str,
                     api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit an algorithm for resource estimation.
        
        Args:
            algorithm_file: Path to the algorithm Python file
            spec_file: Path to the YAML specification file
            api_key: Optional API key for authentication
        
        Returns:
            Dictionary containing the results and artifact URLs
        """
        # Read algorithm file
        with open(algorithm_file, 'r') as f:
            algorithm_code = f.read()
        
        # Read spec file
        with open(spec_file, 'r') as f:
            spec_data = yaml.safe_load(f)
        
        # Prepare request
        payload = {
            'algorithm_code': algorithm_code,
            'spec': spec_data
        }
        
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        # Submit to API
        response = self.session.post(
            f"{self.api_url}/run-algorithm",
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def get_status(self, run_id: str, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Check the status of a running algorithm.
        
        Args:
            run_id: The run ID returned from run_algorithm
            api_key: Optional API key for authentication
        
        Returns:
            Dictionary containing the current status
        """
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        response = self.session.get(
            f"{self.api_url}/status/{run_id}",
            headers=headers
        )
        
        if response.status_code != 200:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    def download_artifact(self, artifact_url: str, output_path: str) -> None:
        """
        Download an artifact from the API.
        
        Args:
            artifact_url: URL of the artifact to download
            output_path: Local path to save the artifact
        """
        response = self.session.get(artifact_url)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)


# Convenience function for quick usage
def run_algorithm(algorithm_file: str, 
                 spec_file: str, 
                 api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to run an algorithm.
    
    Args:
        algorithm_file: Path to the algorithm Python file
        spec_file: Path to the YAML specification file
        api_key: Optional API key for authentication
    
    Returns:
        Dictionary containing the results and artifact URLs
    """
    client = QernelClient()
    return client.run_algorithm(algorithm_file, spec_file, api_key)
