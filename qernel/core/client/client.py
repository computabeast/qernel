"""
Main client class for submitting quantum algorithms to the Qernel resource estimation API.
"""

import logging
import base64
import time
import json
from typing import Dict, Any, Optional, Iterator, Union
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
        # Ensure logs show up for users by default
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Provide a reusable HTTP session for connection pooling
        self.session = requests.Session()
        
        try:
            self.config.validate()
        except QernelAPIError as e:
            self.logger.warning(f"Configuration validation failed: {e}")
    
    def run_algorithm(self, algorithm_instance: Algorithm, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Submit an algorithm instance for resource estimation.
        
        Args:
            algorithm_instance: An instance of Algorithm to be executed
            params: Optional parameter dictionary to pass to the algorithm
            
        Returns:
            Dict containing the API response
            
        Raises:
            QernelAPIError: If the request fails
        """
        total_t0 = time.perf_counter()
        cls = algorithm_instance.__class__
        self.logger.info(f"Preparing to submit algorithm instance: {cls.__module__}.{cls.__name__}")
        
        # Serialize the algorithm instance using cloudpickle
        t0 = time.perf_counter()
        try:
            serialized_algorithm = cloudpickle.dumps(algorithm_instance)
        except Exception as e:
            self.logger.error(f"Serialization failed: {e}")
            raise
        t1 = time.perf_counter()
        self.logger.info(f"Serialized algorithm (bytes={len(serialized_algorithm)} in {t1 - t0:.3f}s)")
        
        # Encode as base64 for JSON serialization
        try:
            encoded_algorithm = base64.b64encode(serialized_algorithm).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Base64 encoding failed: {e}")
            raise
        self.logger.info(f"Base64 size (chars)={len(encoded_algorithm)}")
        
        # Prepare the request (match API style in example)
        base_url = self.config.api_url.rstrip('/')
        url = f"{base_url}/run"
        masked_key = None
        if self.config.api_key and len(self.config.api_key) >= 8:
            masked_key = f"{self.config.api_key[:4]}...{self.config.api_key[-4:]}"
        elif self.config.api_key:
            masked_key = "[set]"
        else:
            masked_key = "[missing]"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-api-key': self.config.api_key
        }
        payload: Dict[str, Any] = {'algorithm_pickle': encoded_algorithm}
        if params is not None:
            payload['params'] = params
        
        self.logger.info(f"POST {url} (timeout={self.config.timeout}s, x-api-key={masked_key})")
        t_req = time.perf_counter()
        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout,
            )
            dt = time.perf_counter() - t_req
            self.logger.info(f"Response received (status={response.status_code}, dt={dt:.3f}s, body_len={len(response.text)})")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                except Exception as e:
                    self.logger.error(f"JSON parse failed: {e}")
                    raise QernelAPIError(f"Failed to parse JSON response: {e}")
                total_dt = time.perf_counter() - total_t0
                self.logger.info(f"Algorithm submitted successfully (total={total_dt:.3f}s)")
                return result
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text[:300]}...")
                raise QernelAPIError(
                    f"API request failed: {response.status_code} - {response.text}",
                    response.status_code,
                    response.text,
                )
        except requests.exceptions.RequestException as e:
            dt = time.perf_counter() - t_req
            self.logger.error(f"Request error after {dt:.3f}s: {e.__class__.__name__}: {e}")
            raise QernelAPIError(f"Request failed: {str(e)}")

    def stream_algorithm(self, algorithm_instance: Algorithm, params: Optional[Dict[str, Any]] = None, parse_json: bool = True) -> Iterator[Union[str, Dict[str, Any]]]:
        """
        Submit an algorithm and stream results via Server-Sent Events (SSE).

        Args:
            algorithm_instance: An instance of Algorithm to be executed
            params: Optional parameter dictionary to pass to the algorithm
            parse_json: If True, parse SSE data payloads as JSON and yield dicts

        Yields:
            Either raw SSE data strings (without the leading 'data: ') or parsed dicts.

        Raises:
            QernelAPIError: If the request fails
        """
        cls = algorithm_instance.__class__
        self.logger.info(f"Preparing to stream algorithm instance: {cls.__module__}.{cls.__name__}")

        # Serialize and encode the algorithm instance
        try:
            serialized_algorithm = cloudpickle.dumps(algorithm_instance)
            encoded_algorithm = base64.b64encode(serialized_algorithm).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to serialize algorithm for streaming: {e}")
            raise

        base_url = self.config.api_url.rstrip('/')
        url = f"{base_url}/stream"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'x-api-key': self.config.api_key
        }
        payload: Dict[str, Any] = {'algorithm_pickle': encoded_algorithm}
        if params is not None:
            payload['params'] = params

        self.logger.info(f"POST {url} (stream=True)")
        try:
            with self.session.post(url, json=payload, headers=headers, stream=True, timeout=self.config.timeout) as response:
                if response.status_code != 200:
                    body_preview = response.text[:300]
                    self.logger.error(f"Streaming request failed: {response.status_code} - {body_preview}...")
                    raise QernelAPIError(
                        f"Streaming request failed: {response.status_code} - {response.text}",
                        response.status_code,
                        response.text,
                    )

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    # Expect lines like: "data: {json}\n\n"
                    if isinstance(line, str) and line.startswith("data: "):
                        data_str = line[6:]
                        if parse_json:
                            try:
                                yield json.loads(data_str)
                                continue
                            except Exception:
                                # Fall back to raw string if not JSON
                                pass
                        yield data_str
                    else:
                        # Yield non-standard lines raw for maximum visibility
                        yield line
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Streaming request error: {e.__class__.__name__}: {e}")
            raise QernelAPIError(f"Streaming request failed: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the Qernel API."""
        url = f"{self.config.api_url}/"
        headers = {
            'Accept': 'application/json',
            'x-api-key': self.config.api_key
        }
        masked_key = None
        if self.config.api_key and len(self.config.api_key) >= 8:
            masked_key = f"{self.config.api_key[:4]}...{self.config.api_key[-4:]}"
        elif self.config.api_key:
            masked_key = "[set]"
        else:
            masked_key = "[missing]"
        self.logger.info(f"GET {url} (x-api-key={masked_key})")
        try:
            t0 = time.perf_counter()
            response = self.session.get(url, headers=headers, timeout=self.config.timeout)
            dt = time.perf_counter() - t0
            self.logger.info(f"Connection check status={response.status_code} dt={dt:.3f}s")
            return {
                'status': 'success' if response.status_code == 200 else 'error',
                'message': 'Connection successful' if response.status_code == 200 else f'Connection failed with status {response.status_code}',
                'response': response.json() if response.status_code == 200 else response.text
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Connection failed: {e}")
            return {'status': 'error', 'message': f'Connection failed: {str(e)}', 'response': None}
        
