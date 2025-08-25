"""Client for interacting with the Qernel resource estimation API."""

import base64
import json
import logging
import time
from datetime import datetime
from collections.abc import Iterator, Mapping
from typing import Any, Optional, TYPE_CHECKING, Union

import requests
import cloudpickle

from qernel.core.client.exceptions import QernelAPIError
from qernel.core.client.config import QernelConfig
from qernel.core.algorithm import Algorithm
from qernel.core.client.models import StreamEvent, AlgorithmTranscript


from qernel.vis.visualizer import AlgorithmVisualizer
from qernel.vis.terminal import TerminalPrinter


class QernelClient:
    """Client for submitting quantum algorithms to the Qernel API.

    Manages HTTP session lifecycle, provides streaming and high-level
    orchestration helpers, and aggregates a transcript of results.
    """
    
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
            self.logger.warning(
                "Configuration validation failed: %s", e
            )

    def _get_base_url(self) -> str:
        return self.config.api_url.rstrip('/')

    def _mask_api_key(self) -> str:
        api_key = self.config.api_key
        if api_key and len(api_key) >= 8:
            return f"{api_key[:4]}...{api_key[-4:]}"
        elif api_key:
            return "[set]"
        else:
            return "[missing]"

    def _build_headers(self, accept: str) -> dict[str, str]:
        headers: dict[str, str] = {
            'Content-Type': 'application/json',
            'Accept': accept,
        }
        if self.config.api_key:
            headers['x-api-key'] = self.config.api_key
        return headers
    
    def _serialize_algorithm(self, algorithm_instance: Algorithm) -> str:
        """Serialize an algorithm instance and return base64-encoded string."""
        try:
            serialized_algorithm = cloudpickle.dumps(algorithm_instance)
            encoded_algorithm = base64.b64encode(serialized_algorithm).decode(
                'utf-8'
            )
            return encoded_algorithm
        except Exception as e:
            self.logger.error("Algorithm serialization failed: %s", e)
            raise
    
    def _build_stream_endpoint(self) -> str:
        """Return the absolute URL for the streaming endpoint."""
        base_url = self._get_base_url()
        return f"{base_url}/stream"
    
    def _prepare_stream_payload(
        self,
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Return the JSON payload for streaming requests."""
        encoded_algorithm = self._serialize_algorithm(algorithm_instance)
        payload: dict[str, Any] = {'algorithm_pickle': encoded_algorithm}
        if params is not None:
            # Convert Mapping to a concrete dict for JSON serialization.
            payload['params'] = dict(params)
        return payload
    
    def _iter_sse_events(
        self, response, parse_json: bool
    ) -> Iterator[Union[str, dict[str, Any]]]:
        """Yield parsed SSE events from a requests streaming response."""
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if isinstance(line, str) and line.startswith("data: "):
                data_str = line[6:]
                if parse_json:
                    try:
                        yield json.loads(data_str)
                        continue
                    except Exception:
                        pass
                yield data_str
            else:
                yield line

    def _decode_circuit_artifacts_in_place(self, analysis: Mapping[str, Any]) -> None:
        """Decode circuit_json_b64 into circuit_json in-place if present."""
        try:
            artifacts = (analysis or {}).get('artifacts') or {}
            b64 = artifacts.get('circuit_json_b64')
            if not b64:
                return
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

    def _status_level_from_stage(self, stage: str) -> str:
        """Return a status level derived from a stage suffix."""
        if stage.endswith(":ok"):
            return "success"
        if stage.endswith(":err"):
            return "error"
        return "info"

    def _print_status(
        self,
        printer: "TerminalPrinter",
        visualizer: Optional["AlgorithmVisualizer"],
        prefix: str,
        msg: str,
        level: str = "info",
    ) -> None:
        """Print status to terminal and optional visualizer."""
        if prefix and prefix != "[status]":
            printer.print_status(prefix.strip("[]"), msg, level=level)
        else:
            printer.print_status("", msg, level=level)
        if visualizer is not None:
            try:
                visualizer.update_status(msg, level=level)
            except Exception:
                # Visualization errors are non-fatal.
                pass

    def stream_events(
        self,
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]] = None,
        parse_json: bool = True,
    ) -> Iterator[Union[str, dict[str, Any]]]:
        """Stream Server-Sent Events (SSE) from the server.

        Yields:
          Either raw 'data:' payload strings or parsed dicts when
          parse_json is True.

        Raises:
          QernelAPIError: If the streaming request fails.
        """
        cls = algorithm_instance.__class__
        self.logger.info(
            "Preparing to stream algorithm instance: %s.%s",
            cls.__module__,
            cls.__name__,
        )

        url = self._build_stream_endpoint()
        headers = self._build_headers('text/event-stream')
        try:
            payload = self._prepare_stream_payload(algorithm_instance, params)
        except Exception as e:
            self.logger.error(
                "Failed to serialize algorithm for streaming: %s", e
            )
            raise

        self.logger.info(
            "POST %s (stream=True, timeout=%ss)", url, self.config.stream_timeout
        )
        try:
            with self.session.post(
                url,
                json=payload,
                headers=headers,
                stream=True,
                timeout=self.config.stream_timeout,
            ) as response:
                if response.status_code != 200:
                    body_preview = response.text[:300]
                    self.logger.error(
                        "Streaming request failed: %d - %s...",
                        response.status_code,
                        body_preview,
                    )
                    raise QernelAPIError(
                        (
                            "Streaming request failed: %d - %s"
                            % (response.status_code, response.text)
                        ),
                        response.status_code,
                        response.text,
                    )
                yield from self._iter_sse_events(response, parse_json=parse_json)
        except requests.exceptions.RequestException as e:
            self.logger.error(
                "Streaming request error: %s: %s", e.__class__.__name__, e
            )
            raise QernelAPIError(f"Streaming request failed: {str(e)}")

    

    def stream_algorithm(
        self,
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]] = None,
        parse_json: bool = True,
    ) -> Iterator[Union[str, dict[str, Any]]]:
        """Deprecated: use stream_events.

        This wrapper maintains backward compatibility.
        """
        self.logger.warning(
            "stream_algorithm is deprecated; use stream_events instead."
        )
        yield from self.stream_events(algorithm_instance, params=params, parse_json=parse_json)

    def run_stream_with_handler(
        self,
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]] = None,
        visualizer: Optional["AlgorithmVisualizer"] = None,
    ) -> AlgorithmTranscript:
        """Consume events, aggregate a transcript, and update sinks.

        Updates the terminal and optional HTML visualizer while enforcing an
        all-or-nothing policy.

        Raises:
          QernelAPIError: With partial transcript on error.
        """
        transcript = AlgorithmTranscript()
        printer = TerminalPrinter()

        try:
            for evt in self.stream_events(
                algorithm_instance, params=params, parse_json=True
            ):
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
                    self._print_status(printer, visualizer, "[start]", se.message or "")
                elif se.type == "status":
                    stage = se.stage or ""
                    msg = se.message or ""
                    level = self._status_level_from_stage(stage)
                    full_msg = (f"{stage} {msg}".strip() if stage else msg)
                    self._print_status(printer, visualizer, "[status]", full_msg, level=level)

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
                        # Decode optional artifacts for convenience
                        try:
                            analysis = getattr(se.response, 'analysis', None) or {}
                            self._decode_circuit_artifacts_in_place(analysis)
                        except Exception:
                            pass

                        transcript.response = se.response
                        transcript.methods = se.response.methods
                        transcript.class_name = se.response.class_
                        transcript.class_doc = se.response.class_doc

                        # Compact grouped summary to terminal
                        mp = transcript.methods
                        printer.print_result_summary(
                            class_name=transcript.class_name,
                            class_doc=transcript.class_doc,
                            methods=mp.model_dump(),
                        )

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

    def run_stream(
        self,
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]] = None,
        visualize: bool = True,
        visualizer: Optional["AlgorithmVisualizer"] = None,
    ) -> AlgorithmTranscript:
        """Single entry point to stream an algorithm with optional visualization.

        If visualize is True, this manages the GUI lifecycle on the main thread
        and consumes the SSE stream in pywebview's startup worker via a
        callback.

        Returns:
          Aggregated AlgorithmTranscript.
        """
        if not visualize:
            return self.run_stream_with_handler(
                algorithm_instance, params=params, visualizer=None
            )

        # Lazily import to avoid circular imports at module import time
        try:
            from qernel.vis.visualizer import AlgorithmVisualizer  # type: ignore
        except Exception:
            # If visualization is requested but unavailable, fall back to headless
            return self.run_stream_with_handler(
                algorithm_instance, params=params, visualizer=None
            )

        algo_name = None
        try:
            algo_name = getattr(algorithm_instance, "get_name", None)
            algo_name = algo_name() if callable(algo_name) else None
        except Exception:
            algo_name = None
        if not algo_name:
            algo_name = f"{algorithm_instance.__class__.__name__}"

        vis = visualizer or AlgorithmVisualizer(algorithm_name=str(algo_name))

        transcript: Optional[AlgorithmTranscript] = None
        error: Optional[Exception] = None

        def _consume_stream() -> None:
            nonlocal transcript, error
            try:
                transcript = self.run_stream_with_handler(
                    algorithm_instance, params=params, visualizer=vis
                )
            except Exception as e:
                error = e

        # Start the GUI on the main thread; SSE runs in webview's startup worker
        vis.start_and_run(on_start=_consume_stream)

        if error is not None:
            # Re-raise, preserving QernelAPIError if that's what occurred
            if isinstance(error, QernelAPIError):
                raise error
            raise QernelAPIError(str(error), transcript=transcript.to_jsonable() if transcript else None)

        if transcript is None:
            # Should not happen, but ensure we return a valid object.
            transcript = AlgorithmTranscript()
        return transcript
    
    def close(self) -> None:
        """Close underlying HTTP session."""
        try:
            self.session.close()
        except Exception:
            pass
    
    def __enter__(self) -> "QernelClient":
        return self
    
    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
    
    def test_connection(self) -> dict[str, Any]:
        """Test the connection to the Qernel API."""
        url = f"{self.config.api_url}/"
        headers = self._build_headers('application/json')
        masked_key = self._mask_api_key()
        self.logger.info("GET %s (x-api-key=%s)", url, masked_key)
        try:
            t0 = time.perf_counter()
            response = self.session.get(
                url, headers=headers, timeout=self.config.timeout
            )
            dt = time.perf_counter() - t0
            self.logger.info(
                "Connection check status=%d dt=%.3fs", response.status_code, dt
            )
            return {
                'status': 'success' if response.status_code == 200 else 'error',
                'message': (
                    'Connection successful'
                    if response.status_code == 200
                    else f'Connection failed with status {response.status_code}'
                ),
                'response': (
                    response.json() if response.status_code == 200 else response.text
                ),
            }
        except requests.exceptions.RequestException as e:
            self.logger.error("Connection failed: %s", e)
            return {
                'status': 'error',
                'message': f'Connection failed: {str(e)}',
                'response': None,
            }
        
