"""
Main client class for submitting quantum algorithms to the Qernel resource estimation API.
"""

import yaml
import os
import logging
import threading
from typing import Dict, Any, Optional
import requests

from .exceptions import QernelAPIError
from .config import QernelConfig


class QernelClient:
    """Client for submitting quantum algorithms to the Qernel resource estimation API."""
    
    def __init__(self, config: Optional[QernelConfig] = None):
        self.config = config or QernelConfig()
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.session.headers.update(self.config.get_headers())
        
        try:
            self.config.validate()
        except QernelAPIError as e:
            self.logger.warning(f"Configuration validation failed: {e}")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic."""
        url = f"{self.config.api_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(self.config.max_retries):
            try:
                response = getattr(self.session, method.lower())(
                    url, timeout=self.config.timeout, **kwargs
                )
                if response.status_code == 200:
                    return response
                elif attempt == self.config.max_retries - 1:
                    raise QernelAPIError(
                        f"API request failed: {response.status_code} - {response.text}",
                        response.status_code, response.text
                    )
                else:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {response.status_code}")
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise QernelAPIError(f"Request failed after {self.config.max_retries} attempts: {str(e)}")
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
    
    def _read_files(self, algorithm_file: str, spec_file: str) -> tuple[str, dict]:
        """Read and validate algorithm and spec files."""
        for file_path, file_type in [(algorithm_file, "Algorithm"), (spec_file, "Specification")]:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"{file_type} file not found: {file_path}")
        
        with open(algorithm_file, 'r') as f:
            algorithm_code = f.read()
        with open(spec_file, 'r') as f:
            spec_data = yaml.safe_load(f)
        
        return algorithm_code, spec_data
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the Qernel API."""
        try:
            response = self.session.get(f"{self.config.api_url}/", timeout=self.config.timeout)
            return {
                'status': 'success' if response.status_code == 200 else 'error',
                'message': 'Connection successful' if response.status_code == 200 else f'Connection failed with status {response.status_code}',
                'response': response.json() if response.status_code == 200 else response.text
            }
        except requests.exceptions.RequestException as e:
            return {'status': 'error', 'message': f'Connection failed: {str(e)}', 'response': None}
    
    def run_algorithm(self, algorithm_file: str, spec_file: str) -> Dict[str, Any]:
        """Submit an algorithm for resource estimation."""
        algorithm_code, spec_data = self._read_files(algorithm_file, spec_file)
        payload = {'algorithm_code': algorithm_code, 'spec': spec_data}
        
        self.logger.info("Submitting algorithm to Qernel API...")
        response = self._make_request('POST', '/run-algorithm', json=payload)
        result = response.json()
        self.logger.info("Algorithm submitted successfully")
        return result
    
    def run_algorithm_with_visualization(self, algorithm_file: str, spec_file: str) -> Dict[str, Any]:
        """Submit an algorithm for resource estimation with real-time visualization."""
        from ...vis.visualizer import AlgorithmVisualizer
        
        visualizer = AlgorithmVisualizer(algorithm_file, spec_file)
        result_container = {'result': None, 'error': None}
        
        def run_algorithm_thread():
            try:
                result = self._run_algorithm_with_streaming(algorithm_file, spec_file, visualizer)
                result_container['result'] = result
                visualizer.update_with_results(result)
            except Exception as e:
                result_container['error'] = e
                visualizer.update_status(f"Error: {str(e)}", "error")
        
        algorithm_thread = threading.Thread(target=run_algorithm_thread, daemon=True)
        algorithm_thread.start()
        visualizer.start_and_run()
        algorithm_thread.join()
        
        if result_container['error']:
            raise result_container['error']
        return result_container['result']
    
    def _run_algorithm_with_streaming(self, algorithm_file: str, spec_file: str, visualizer) -> Dict[str, Any]:
        """Internal method to run algorithm with streaming updates to visualizer."""
        algorithm_code, spec_data = self._read_files(algorithm_file, spec_file)
        payload = {'algorithm_code': algorithm_code, 'spec': spec_data}
        
        visualizer.update_status("Submitting algorithm to Qernel API...")
        response = self.session.post(
            f"{self.config.api_url}/run-algorithm",
            json=payload, timeout=self.config.timeout
        )
        
        if response.status_code != 200:
            error_msg = f"API request failed: {response.status_code} - {response.text}"
            visualizer.update_status(f"Error: {error_msg}")
            raise QernelAPIError(error_msg, response.status_code, response.text)
        
        result = response.json()
        if 'run_id' in result:
            visualizer.update_status(f"Algorithm submitted successfully. Run ID: {result['run_id']}")
        return result
    
    def get_status(self, run_id: str) -> Dict[str, Any]:
        """Check the status of a running algorithm."""
        try:
            response = self.session.get(
                f"{self.config.api_url}/status/{run_id}", timeout=self.config.timeout
            )
            if response.status_code == 200:
                return response.json()
            else:
                raise QernelAPIError(
                    f"Status check failed: {response.status_code} - {response.text}",
                    response.status_code, response.text
                )
        except requests.exceptions.RequestException as e:
            raise QernelAPIError(f"Status check request failed: {str(e)}")
    
    def download_artifact(self, artifact_url: str, output_path: str) -> None:
        """Download an artifact from the API."""
        try:
            response = self.session.get(artifact_url, stream=True, timeout=self.config.timeout)
            response.raise_for_status()
            
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            self.logger.info(f"Artifact downloaded successfully to {output_path}")
        except requests.exceptions.RequestException as e:
            raise QernelAPIError(f"Failed to download artifact: {str(e)}")
        except IOError as e:
            raise QernelAPIError(f"Failed to save artifact: {str(e)}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
