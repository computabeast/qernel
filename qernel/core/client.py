"""
Qernel Client for submitting quantum algorithms to the resource estimation API.
"""

import json
import yaml
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import requests
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class QernelAPIError(Exception):
    """Custom exception for Qernel API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


@dataclass
class QernelConfig:
    """Configuration class for Qernel client settings."""
    
    api_url: str = "https://d3nt1x9f8mnu77.cloudfront.net"
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    
    def __post_init__(self):
        """Initialize configuration with environment variables."""
        # Load API key from environment if not provided
        if self.api_key is None:
            self.api_key = os.getenv('QERNEL_API_KEY')
        
        # Validate configuration
        if not self.api_key:
            logging.warning("No API key provided. Set QERNEL_API_KEY environment variable or pass api_key parameter.")
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['x-api-key'] = self.api_key
        
        return headers
    
    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.api_key:
            raise QernelAPIError("API key is required. Set QERNEL_API_KEY environment variable or pass api_key parameter.")
        return True


class QernelClient:
    """Client for submitting quantum algorithms to the Qernel resource estimation API."""
    
    def __init__(self, config: Optional[QernelConfig] = None):
        """
        Initialize the client.
        
        Args:
            config: Configuration object. If None, creates default config with env vars.
        """
        self.config = config or QernelConfig()
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        
        # Configure session
        self.session.headers.update(self.config.get_headers())
        
        # Validate configuration
        try:
            self.config.validate()
        except QernelAPIError as e:
            self.logger.warning(f"Configuration validation failed: {e}")
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection to the Qernel API.
        
        Returns:
            Dictionary containing connection test results
        """
        try:
            response = self.session.get(
                f"{self.config.api_url}/",
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'message': 'Connection successful',
                    'response': response.json()
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Connection failed with status {response.status_code}',
                    'response': response.text
                }
                
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'message': f'Connection failed: {str(e)}',
                'response': None
            }
    
    def run_algorithm(self, 
                     algorithm_file: str, 
                     spec_file: str) -> Dict[str, Any]:
        """
        Submit an algorithm for resource estimation.
        
        Args:
            algorithm_file: Path to the algorithm Python file
            spec_file: Path to the YAML specification file
        
        Returns:
            Dictionary containing the results and artifact URLs
            
        Raises:
            QernelAPIError: If the API request fails
            FileNotFoundError: If algorithm or spec files don't exist
        """
        # Validate files exist
        if not os.path.exists(algorithm_file):
            raise FileNotFoundError(f"Algorithm file not found: {algorithm_file}")
        if not os.path.exists(spec_file):
            raise FileNotFoundError(f"Specification file not found: {spec_file}")
        
        # Read algorithm file
        with open(algorithm_file, 'r') as f:
            algorithm_code = f.read()
        
        # Read spec file
        with open(spec_file, 'r') as f:
            spec_data = yaml.safe_load(f)
        
        # Prepare request payload
        payload = {
            'algorithm_code': algorithm_code,
            'spec': spec_data
        }
        
        self.logger.info("Submitting algorithm to Qernel API...")
        
        # Submit to API with retry logic
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    f"{self.config.api_url}/run-algorithm",
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.info("Algorithm submitted successfully")
                    return result
                else:
                    error_msg = f"API request failed: {response.status_code} - {response.text}"
                    if attempt == self.config.max_retries - 1:
                        raise QernelAPIError(error_msg, response.status_code, response.text)
                    else:
                        self.logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")
                        
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise QernelAPIError(f"Request failed after {self.config.max_retries} attempts: {str(e)}")
                else:
                    self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
    
    def run_algorithm_with_visualization(self,
                                       algorithm_file: str,
                                       spec_file: str) -> Dict[str, Any]:
        """
        Submit an algorithm for resource estimation with real-time visualization.
        
        Args:
            algorithm_file: Path to the algorithm Python file
            spec_file: Path to the YAML specification file
        
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
                    algorithm_file, spec_file, visualizer
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
                                    visualizer) -> Dict[str, Any]:
        """
        Internal method to run algorithm with streaming updates to visualizer.
        
        Args:
            algorithm_file: Path to the algorithm Python file
            spec_file: Path to the YAML specification file
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
        
        # Prepare request payload
        payload = {
            'algorithm_code': algorithm_code,
            'spec': spec_data
        }
        
        # Update visualization with initial status
        visualizer.update_status("Submitting algorithm to Qernel API...")
        
        # Submit to API
        response = self.session.post(
            f"{self.config.api_url}/run-algorithm",
            json=payload,
            timeout=self.config.timeout
        )
        
        if response.status_code != 200:
            error_msg = f"API request failed: {response.status_code} - {response.text}"
            visualizer.update_status(f"Error: {error_msg}")
            raise QernelAPIError(error_msg, response.status_code, response.text)
        
        result = response.json()
        
        # Update visualization with run ID if available
        if 'run_id' in result:
            visualizer.update_status(f"Algorithm submitted successfully. Run ID: {result['run_id']}")
        
        return result
    
    def get_status(self, run_id: str) -> Dict[str, Any]:
        """
        Check the status of a running algorithm.
        
        Args:
            run_id: The run ID returned from run_algorithm
        
        Returns:
            Dictionary containing the current status
            
        Raises:
            QernelAPIError: If the API request fails
        """
        try:
            response = self.session.get(
                f"{self.config.api_url}/status/{run_id}",
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise QernelAPIError(
                    f"Status check failed: {response.status_code} - {response.text}",
                    response.status_code,
                    response.text
                )
                
        except requests.exceptions.RequestException as e:
            raise QernelAPIError(f"Status check request failed: {str(e)}")
    
    def download_artifact(self, artifact_url: str, output_path: str) -> None:
        """
        Download an artifact from the API.
        
        Args:
            artifact_url: URL of the artifact to download
            output_path: Local path to save the artifact
            
        Raises:
            QernelAPIError: If the download fails
        """
        try:
            response = self.session.get(artifact_url, stream=True, timeout=self.config.timeout)
            response.raise_for_status()
            
            # Ensure output directory exists
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
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()
