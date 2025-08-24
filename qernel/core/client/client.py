"""
Main client class for submitting quantum algorithms to the Qernel resource estimation API.
"""

import logging
import base64
import time
import json
from typing import Dict, Any, Optional, Iterator, Union, List, TYPE_CHECKING
import requests
import cloudpickle

from .exceptions import QernelAPIError
from .config import QernelConfig
from ..algorithm import Algorithm
from pydantic import BaseModel, Field
from datetime import datetime
from .models import (
    StreamEvent,
    AlgorithmTranscript,
    AlgorithmResponse,
    MethodsPayload,
)

if TYPE_CHECKING:
    from qernel.vis.visualizer import AlgorithmVisualizer


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
        # Use same endpoint as non-streaming, server responds with SSE if Accept header set
        url = f"{base_url}/run"
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'x-api-key': self.config.api_key
        }
        payload: Dict[str, Any] = {'algorithm_pickle': encoded_algorithm}
        if params is not None:
            payload['params'] = params

        self.logger.info(f"POST {url} (stream=True, timeout={self.config.stream_timeout}s)")
        try:
            with self.session.post(url, json=payload, headers=headers, stream=True, timeout=self.config.stream_timeout) as response:
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

    def run_stream_with_handler(self, algorithm_instance: Algorithm, params: Optional[Dict[str, Any]] = None, visualizer: Optional["AlgorithmVisualizer"] = None) -> AlgorithmTranscript:
        """
        High-level OOP runner that consumes streaming events, aggregates a transcript,
        updates terminal and optional HTML visualizer, and enforces all-or-nothing policy.
        
        Raises QernelAPIError with partial transcript on error.
        """
        transcript = AlgorithmTranscript()

        def _print_status(prefix: str, msg: str, level: str = "info") -> None:
            print(f"{prefix} {msg}")
            if visualizer is not None:
                try:
                    visualizer.update_status(msg, level=level)
                except Exception:
                    pass

        try:
            for evt in self.stream_algorithm(algorithm_instance, params=params, parse_json=True):
                if isinstance(evt, dict):
                    try:
                        se = StreamEvent.model_validate(evt)
                    except Exception:
                        # Unknown dict, forward minimal info
                        print(evt)
                        continue
                else:
                    print(evt)
                    continue

                transcript.add_event(se)

                if se.type == "start":
                    _print_status("[start]", se.message or "")
                elif se.type == "status":
                    stage = se.stage or ""
                    msg = se.message or ""
                    # Determine level by stage suffix
                    level = "info"
                    if stage.endswith(":ok"):
                        level = "success"
                    elif stage.endswith(":err"):
                        level = "error"

                    if stage:
                        _print_status("[status]", f"{stage} {msg}".strip(), level=level)
                    else:
                        _print_status("[status]", msg, level=level)

                    # Update aggregate methods payload on known stages
                    if stage.startswith("get_name:ok") and se.result is not None:
                        transcript.methods.get_name_result = str(se.result)
                    elif stage.startswith("get_type:ok") and se.result is not None:
                        transcript.methods.get_type_result = str(se.result)
                    elif stage.startswith("build_circuit:ok"):
                        if se.summary is not None:
                            transcript.methods.build_circuit_summary = se.summary
                        if se.obj_type is not None:
                            transcript.methods.build_circuit_type = se.obj_type

                    # Do not hard-fail on per-pass errors; continue to await final result
                    # Users can inspect pipeline details in the final result.

                elif se.type == "error":
                    transcript.ended_reason = "error"
                    raise QernelAPIError(
                        message=se.message or se.error or "Unknown streaming error",
                        transcript=transcript.to_jsonable(),
                    )
                elif se.type == "result":
                    if se.response is not None:
                        # Decode optional circuit_json_b64 into circuit_json for convenience
                        try:
                            analysis = getattr(se.response, 'analysis', None) or {}
                            artifacts = (analysis or {}).get('artifacts') or {}
                            b64 = artifacts.get('circuit_json_b64')
                            if b64:
                                try:
                                    decoded = base64.b64decode(b64).decode('utf-8')
                                    try:
                                        artifacts['circuit_json'] = json.loads(decoded)
                                    except Exception:
                                        artifacts['circuit_json'] = decoded
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        transcript.response = se.response
                        transcript.methods = se.response.methods
                        transcript.class_name = se.response.class_
                        transcript.class_doc = se.response.class_doc

                        # Compact grouped summary to terminal
                        print("\n=== Result ===")
                        if transcript.class_name:
                            print(f"Class: {transcript.class_name}")
                        if transcript.class_doc:
                            print(f"Doc: {transcript.class_doc}")
                        mp = transcript.methods
                        if mp.get_name_result is not None:
                            print(f"Name: {mp.get_name_result}")
                        if mp.get_type_result is not None:
                            print(f"Type: {mp.get_type_result}")
                        if mp.build_circuit_summary is not None:
                            print("Circuit (ascii):")
                            print(mp.build_circuit_summary)

                        # Update visualizer final results
                        if visualizer is not None:
                            try:
                                # Prefer full response dict including analysis
                                full_response = se.response.model_dump(by_alias=True)
                                visualizer.update_with_results(full_response)
                            except Exception:
                                try:
                                    visualizer.update_with_results(
                                        {
                                            "class": transcript.class_name,
                                            "class_doc": transcript.class_doc,
                                            "methods": mp.model_dump(),
                                        }
                                    )
                                except Exception:
                                    pass
                elif se.type == "done":
                    transcript.ended_reason = "done"
                    transcript.ended_at = datetime.utcnow()
                    break

            # Drain complete; ensure end time is set if not already
            if transcript.ended_at is None:
                transcript.ended_at = datetime.utcnow()
            return transcript

        except QernelAPIError:
            if transcript.ended_at is None:
                transcript.ended_at = datetime.utcnow()
            raise
        except Exception as e:
            if transcript.ended_at is None:
                transcript.ended_at = datetime.utcnow()
            # Wrap unexpected errors with transcript
            raise QernelAPIError(str(e), transcript=transcript.to_jsonable())
    
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
        
