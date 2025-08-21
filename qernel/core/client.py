"""
Qernel Client for submitting quantum algorithms to the resource estimation API.
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
    
    def run_algorithm_with_visualization(self,
                                       algorithm_file: str,
                                       spec_file: str,
                                       api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit an algorithm for resource estimation with real-time visualization.
        
        Args:
            algorithm_file: Path to the algorithm Python file
            spec_file: Path to the YAML specification file
            api_key: Optional API key for authentication
        
        Returns:
            Dictionary containing the results and artifact URLs
        """
        from ..vis.visualizer import AlgorithmVisualizer
        import threading
        
        # Create visualizer instance
        visualizer = AlgorithmVisualizer(algorithm_file, spec_file)
        
        # Container for result
        result_container = {'result': None, 'error': None}
        
        def run_algorithm_thread():
            """Run algorithm in separate thread."""
            try:
                result = self._run_algorithm_with_streaming(
                    algorithm_file, spec_file, api_key, visualizer
                )
                result_container['result'] = result
                visualizer.update_with_results(result)
            except Exception as e:
                result_container['error'] = e
                visualizer.update_status(f"Error: {str(e)}", "error")
        
        # Start algorithm execution in background thread
        algorithm_thread = threading.Thread(target=run_algorithm_thread)
        algorithm_thread.daemon = True
        algorithm_thread.start()
        
        # Start visualization on main thread (this will block until window closes)
        visualizer.start_and_run()
        
        # Wait for algorithm thread to complete
        algorithm_thread.join()
        
        # Check for errors
        if result_container['error']:
            raise result_container['error']
        
        return result_container['result']
    
    def _run_algorithm_with_streaming(self,
                                    algorithm_file: str,
                                    spec_file: str,
                                    api_key: Optional[str],
                                    visualizer) -> Dict[str, Any]:
        """
        Internal method to run algorithm with streaming updates to visualizer.
        
        Args:
            algorithm_file: Path to the algorithm Python file
            spec_file: Path to the YAML specification file
            api_key: Optional API key for authentication
            visualizer: AlgorithmVisualizer instance to receive updates
        
        Returns:
            Dictionary containing the final results
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
        
        # Update visualization with initial status
        visualizer.update_status("Submitting algorithm to API...")
        
        # Submit to API
        response = self.session.post(
            f"{self.api_url}/run-algorithm",
            json=payload,
            headers=headers
        )
        
        if response.status_code != 200:
            error_msg = f"API request failed: {response.status_code} - {response.text}"
            visualizer.update_status(f"Error: {error_msg}")
            raise Exception(error_msg)
        
        result = response.json()
        
        # Update visualization with run ID if available
        if 'run_id' in result:
            visualizer.update_status(f"Algorithm submitted successfully. Run ID: {result['run_id']}")
        
        return result
    
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
        response = self.session.get(artifact_url, stream=True)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
