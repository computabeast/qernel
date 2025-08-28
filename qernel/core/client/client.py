"""Client for interacting with the Qernel resource estimation API.

# Sections
1) Imports
2) Helpers (artifact decode, task summary)
3) Formatting utilities (terminal logger)
4) Client class (public API):
   - stream_events (HTTP + SSE)
   - run_stream_with_handler (consume + sinks)
   - run_stream (visualize orchestration)
   - connection utilities
"""

import base64
import logging
import json
import os
import sys
import time
from datetime import datetime
from collections.abc import Mapping
from typing import Any, Optional, Iterator, Union

import requests
import cloudpickle

from qernel.core.client.config import QernelConfig, QernelAPIError
from qernel.core.algorithm import Algorithm
from qernel.core.client.models import StreamEvent, AlgorithmTranscript
from qernel.vis.terminal import TerminalPrinter

# Optional: visualizer may be unavailable in some environments
try:
    from qernel.vis.visualizer import AlgorithmVisualizer  # type: ignore
except Exception:  # pragma: no cover
    AlgorithmVisualizer = None  # type: ignore

# --- Helpers ---------------------------------------------------------------

def _decode_circuit_artifacts_in_place(analysis: Mapping[str, Any]) -> None:
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

def _summarize_tasks(build_doc: Optional[str], analysis: Optional[Mapping[str, Any]]) -> list[dict[str, Any]]:
    def _extract_task_specs_from_doc(doc: Optional[str]) -> list[dict[str, Any]]:
        if not doc:
            return []
        text = (doc or "").lower()
        specs: list[dict[str, Any]] = []
        if ("resource" in text) or ("estimate" in text):
            specs.append({'id': 'resource_estimation','title': 'Resource Estimation','keywords': ['resource.qualtran','qualtran','resource','estimate','resource_estimation']})
        if ("mitiq" in text) or ("zne" in text) or ("error mitigation" in text):
            specs.append({'id': 'error_mitigation_zne','title': 'Error Mitigation (Mitiq ZNE)','keywords': ['mitigation.mitiq.zne','mitiq','zne','mitigation']})
        if ("simulate" in text) or ("simulation" in text) or ("histogram" in text) or ("shots" in text):
            specs.append({'id': 'simulation_histogram','title': 'Simulation (Histogram)','keywords': ['execute.simulator','simulator','execute','histogram','counts','shots']})
        return specs
    def _task_payload_slice(analysis: Optional[Mapping[str, Any]], keywords: list[str]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if not analysis:
            return result
        pipeline = (analysis or {}).get('pipeline')
        if isinstance(pipeline, list):
            matched = []
            for p in pipeline:
                name = str((p or {}).get('name', '')).lower()
                if any(kw in name for kw in keywords):
                    matched.append(p)
            if matched:
                if len(matched) == 1:
                    step = matched[0]
                    out = (step or {}).get('output') or {}
                    sl: dict[str, Any] = {}
                    if isinstance(out, Mapping):
                        if 'summary' in out:
                            sl['summary'] = out['summary']
                        for k in ('counts','shots','mitigated_value','raw_value','metrics'):
                            if k in out:
                                sl[k] = out[k]
                    result = {'pipeline': [step], 'output': sl or out}
                else:
                    result = {'pipeline': matched}
        return result
    def _task_details_from_analysis(analysis: Optional[Mapping[str, Any]], keywords: list[str]) -> dict[str, Any]:
        details: dict[str, Any] = {}
        if not analysis:
            return details
        pipeline = (analysis or {}).get('pipeline')
        if isinstance(pipeline, list):
            for p in pipeline:
                name = str((p or {}).get('name', '')).lower()
                if not any(kw in name for kw in keywords):
                    continue
                out = (p or {}).get('output') or {}
                step_sum = out.get('summary') if isinstance(out, Mapping) else None
                if isinstance(step_sum, Mapping):
                    for k in ['t_count','qubit_count','depth','op_counts','mitigated_value']:
                        if k in step_sum:
                            details[k] = step_sum[k]
                for k in ['mitigated_value','raw_value']:
                    if k in out:
                        details[k] = out[k]
                if 'counts' in out and isinstance(out['counts'], Mapping):
                    details['counts'] = out['counts']
                if 'shots' in out:
                    details['shots'] = out['shots']
        return details
    specs = _extract_task_specs_from_doc(build_doc)
    summary: list[dict[str, Any]] = []
    for spec in specs:
        details = _task_details_from_analysis(analysis, spec['keywords'])
        payload = _task_payload_slice(analysis, spec['keywords'])
        status = 'success' if details or payload else 'info'
        summary.append({'id': spec['id'],'title': spec['title'],'status': status,'details': details,'json': payload})
    return summary

 


def _isatty(stream) -> bool:
    try:
        return stream.isatty()
    except Exception:
        return False

# --- Formatting utilities --------------------------------------------------

class _BlueDotFormatter(logging.Formatter):
    """Minimal formatter that prints a small icon instead of [LEVEL].

    INFO  -> cyan •  message
    WARN  -> yellow ! message
    ERROR -> red ✗   message
    DEBUG -> dim   · message
    """

    def __init__(self, enable_color: Optional[bool] = None) -> None:
        super().__init__()
        if enable_color is None:
            enable_color = _isatty(sys.stderr) and os.getenv("NO_COLOR") is None
        self.enable_color = enable_color

    def _ansi(self, code: str, text: str) -> str:
        return f"\x1b[{code}m{text}\x1b[0m" if self.enable_color else text

    def _icon_for(self, levelno: int) -> str:
        if levelno >= logging.ERROR:
            return self._ansi("31", "✗")  # red
        if levelno >= logging.WARNING:
            return self._ansi("33", "!")  # yellow
        if levelno <= logging.DEBUG:
            return self._ansi("90", "·")  # gray dot
        # INFO (default)
        return self._ansi("36", "•")      # cyan dot

    def format(self, record: logging.LogRecord) -> str:
        icon = self._icon_for(record.levelno)
        msg = record.getMessage()
        return f"{icon} {msg}"


# --- Client ----------------------------------------------------------------

class QernelClient:
    """Client for submitting quantum algorithms to the Qernel API.

    Manages HTTP session lifecycle, provides streaming and high-level
    orchestration helpers, and aggregates a transcript of results.
    """
    
    def __init__(self, config: Optional[QernelConfig] = None):
        self.config = config or QernelConfig()
        self.logger = logging.getLogger(__name__)
        # Ensure logs show up for users by default with blue-dot formatting
        if not self.logger.handlers:
            handler = logging.StreamHandler(stream=sys.stderr)
            handler.setFormatter(_BlueDotFormatter())
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

    def _mask_api_key(self) -> str:
        api_key = self.config.api_key
        if api_key and len(api_key) >= 8:
            return f"{api_key[:4]}...{api_key[-4:]}"
        elif api_key:
            return "[set]"
        else:
            return "[missing]"

    def _build_headers(self, accept: str) -> dict[str, str]:
        headers = dict(self.config.get_headers())
        headers['Accept'] = accept
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

    def _status_level_from_stage(self, stage: str) -> str:
        """Return a status level derived from a stage suffix."""
        if stage.endswith(":ok"):
            return "success"
        if stage.endswith(":err"):
            return "error"
        return "info"

    # (status printing handled inline in run_stream_with_handler for clarity)

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

        try:
            payload = self._prepare_stream_payload(algorithm_instance, params)
        except Exception as e:
            self.logger.error("Failed to serialize algorithm for streaming: %s", e)
            raise

        # Build request
        base_url = (self.config.api_url or "").rstrip("/")
        url = f"{base_url}/stream"
        headers = dict(self.config.get_headers())
        headers['Accept'] = 'text/event-stream'
        json_payload = payload
        self.logger.info(
            "POST %s (stream=True, timeout=%ss)", url, self.config.stream_timeout
        )
        try:
            # Warmup spinner and retry/backoff for origin warm-ups (e.g., 504s)
            tprinter = TerminalPrinter()
            tprinter.start_warmup()
            start = time.perf_counter()
            connected = False
            backoff = 2.0

            while True:
                remaining = self.config.stream_timeout - (time.perf_counter() - start)
                if remaining <= 0:
                    raise QernelAPIError("Streaming request timed out while warming up origin")

                try:
                    with self.session.post(
                        url,
                        json=json_payload,
                        headers=headers,
                        stream=True,
                        timeout=remaining,
                    ) as response:
                        if response.status_code != 200:
                            # Common warmup codes: 502/503/504 – retry within total timeout
                            if response.status_code in (502, 503, 504):
                                # brief sleep then retry, keeping spinner running
                                sleep_s = min(backoff, max(0.5, remaining))
                                time.sleep(sleep_s)
                                backoff = min(backoff * 2.0, 10.0)
                                continue
                            body_preview = response.text[:300]
                            raise QernelAPIError(
                                (
                                    "Streaming request failed: %d - %s"
                                    % (response.status_code, body_preview)
                                ),
                                response.status_code,
                                response.text,
                            )

                        # First bytes received – stop warmup
                        if not connected:
                            try:
                                tprinter.finish_warmup(success=True)
                            except Exception:
                                pass
                            connected = True

                        # SSE line iterator
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
                        break  # finished normally
                except requests.exceptions.RequestException:
                    # Network hiccup – retry within total timeout
                    sleep_s = min(backoff, max(0.5, remaining))
                    time.sleep(sleep_s)
                    backoff = min(backoff * 2.0, 10.0)
                    continue
        except QernelAPIError as e:
            # Re-log with context then re-raise
            self.logger.error("Streaming request failed: %s", e.message)
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error("Streaming request error: %s: %s", e.__class__.__name__, e)
            raise QernelAPIError(f"Streaming request failed: {str(e)}")
        finally:
            # Ensure warmup spinner is cleared
            try:
                if 'connected' in locals() and not connected:
                    tprinter.finish_warmup(success=False)
                else:
                    # If already finished successfully, this is a no-op
                    tprinter.finish_warmup(success=True)
            except Exception:
                pass

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
        visualizer: Optional[Any] = None,
    ) -> AlgorithmTranscript:
        """Consume events, aggregate a transcript, and update sinks.

        Updates the terminal and optional HTML visualizer while enforcing an
        all-or-nothing policy.

        Raises:
          QernelAPIError: With partial transcript on error.
        """
        transcript = AlgorithmTranscript()
        printer = TerminalPrinter()
        viz_sink = visualizer  # pass-through; we call methods directly if present
        # Stash a final pipeline summary until the result arrives
        pipeline_done_summary: Optional[Mapping[str, Any]] = None

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
                    printer.print_status("", se.message or "", level="info")
                    if viz_sink is not None:
                        try:
                            viz_sink.update_status(se.message or "", level="info")
                        except Exception:
                            pass
                elif se.type == "status":
                    stage = se.stage or ""
                    msg = se.message or ""
                    level = self._status_level_from_stage(stage)
                    full_msg = (f"{stage} {msg}".strip() if stage else msg)
                    printer.print_status("", full_msg, level=level)
                    if viz_sink is not None:
                        try:
                            viz_sink.update_status(full_msg, level=level)
                        except Exception:
                            pass

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

                    # Stash final pipeline summary for later merge into analysis
                    if stage.startswith("pipeline:done") and isinstance(se.summary, Mapping):
                        pipeline_done_summary = se.summary

                elif se.type == "error":
                    transcript.ended_reason = "error"
                    raise QernelAPIError(
                        message=se.message or se.error or "Unknown streaming error",
                        transcript=transcript.to_jsonable(),
                    )
                elif se.type == "result":
                    if se.response is not None:
                        # Merge any final summary into analysis before further processing
                        try:
                            analysis = getattr(se.response, 'analysis', None) or {}
                            if isinstance(analysis, Mapping) and pipeline_done_summary is not None:
                                merged = dict(analysis)
                                sum0 = dict(merged.get('summary') or {})
                                sum0.update(dict(pipeline_done_summary))
                                merged['summary'] = sum0
                                se.response.analysis = merged
                        except Exception:
                            pass

                        # Decode optional artifacts for convenience
                        try:
                            analysis = getattr(se.response, 'analysis', None) or {}
                            _decode_circuit_artifacts_in_place(analysis)
                        except Exception:
                            pass

                        transcript.response = se.response
                        transcript.methods = se.response.methods
                        transcript.class_name = se.response.class_
                        transcript.class_doc = se.response.class_doc

                        # Build task summary from build_circuit doc and analysis
                        build_doc = transcript.methods.build_circuit_doc
                        task_summary = _summarize_tasks(build_doc, se.response.analysis)

                        # Notify sinks with results
                        full_response: Optional[dict[str, Any]] = None
                        try:
                            full_response = se.response.model_dump(by_alias=True)
                        except Exception:
                            pass
                        # Terminal summary
                        mp = transcript.methods
                        printer.print_result_summary(
                            class_name=transcript.class_name,
                            class_doc=transcript.class_doc,
                            methods=mp.model_dump(),
                        )
                        if task_summary:
                            try:
                                printer.print_task_summary(task_summary)
                            except Exception:
                                pass
                        if viz_sink is not None:
                            try:
                                if full_response is None:
                                    full_response = {
                                        "class": transcript.class_name,
                                        "class_doc": transcript.class_doc,
                                        "methods": transcript.methods.model_dump(),
                                    }
                                if task_summary:
                                    full_response = dict(full_response)
                                    full_response["task_summary"] = task_summary
                                viz_sink.update_with_results(full_response)
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
        finally:
            try:
                printer.finish()
            except Exception:
                pass

    def run_stream(
        self,
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]] = None,
        visualize: bool = True,
        visualizer: Optional[Any] = None,
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

        algo_name = None
        try:
            algo_name = getattr(algorithm_instance, "get_name", None)
            algo_name = algo_name() if callable(algo_name) else None
        except Exception:
            algo_name = None
        if not algo_name:
            algo_name = f"{algorithm_instance.__class__.__name__}"

        # If visualizer library is unavailable and none provided, fall back to headless
        if AlgorithmVisualizer is None and visualizer is None:
            return self.run_stream_with_handler(
                algorithm_instance, params=params, visualizer=None
            )
        vis = visualizer or AlgorithmVisualizer(algorithm_name=str(algo_name))  # type: ignore[name-defined]

        transcript: Optional[AlgorithmTranscript] = None

        def _consume_stream() -> None:
            nonlocal transcript
            try:
                transcript = self.run_stream_with_handler(
                    algorithm_instance, params=params, visualizer=vis
                )
            except Exception:
                # Ignore; transcript remains None and will be defaulted
                pass

        # Start the GUI on the main thread; SSE runs in webview's startup worker
        vis.start_and_run(on_start=_consume_stream)

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
        
