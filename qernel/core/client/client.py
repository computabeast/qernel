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
import binascii
import gzip
import logging
import json
import os
import sys
import time
from datetime import datetime
from collections.abc import Mapping
from typing import Any, Optional, Iterator, Union
from dataclasses import dataclass

import requests
import cloudpickle
# Note: kept imports minimal; model validation errors are handled via try/except

from qernel.core.client.config import QernelConfig, QernelAPIError
from qernel.core.algorithm import Algorithm
from qernel.core.client.models import StreamEvent, AlgorithmTranscript
from qernel.core.client.task_summary import summarize_tasks as _summarize_tasks
from qernel.vis.terminal import TerminalPrinter

# Optional: visualizer may be unavailable in some environments
try:
    from qernel.vis.visualizer import AlgorithmVisualizer as _AlgorithmVisualizer  # type: ignore
    algorithm_visualizer_cls: Optional[type] = _AlgorithmVisualizer
except (ModuleNotFoundError, ImportError):  # pragma: no cover
    algorithm_visualizer_cls: Optional[type] = None

# --- Helpers ---------------------------------------------------------------


def _decode_circuit_artifacts_in_place(analysis: Mapping[str, Any]) -> None:
    artifacts = (analysis or {}).get("artifacts") or {}
    b64 = artifacts.get("circuit_json_b64")
    if not b64:
        return
    try:
        decoded_bytes = base64.b64decode(b64)
    except (binascii.Error, TypeError, ValueError):
        return
    try:
        decoded_str = decoded_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return
    try:
        artifacts["circuit_json"] = json.loads(decoded_str)
    except json.JSONDecodeError:
        artifacts["circuit_json"] = decoded_str


    # Moved task summarization helpers to task_summary.py to keep this module smaller


def _isatty(stream) -> bool:
    try:
        return stream.isatty()
    except (AttributeError, ValueError):
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
        return self._ansi("36", "•")  # cyan dot

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
            self.logger.warning("Configuration validation failed: %s", e)

        # Internal: warmup spinner helper
        class _Warmup:
            def __init__(
                self, *, printer: TerminalPrinter, finish_on_exit: bool = True
            ) -> None:
                self.printer = printer
                self.finish_on_exit = finish_on_exit
                self.connected = False

            def start(self) -> None:
                """Start the warmup spinner."""
                try:
                    self.printer.start_warmup()
                except (AttributeError, RuntimeError):
                    pass

            def mark_connected(self) -> None:
                """Mark the warmup as connected and stop the spinner successfully."""
                if not self.connected:
                    try:
                        self.printer.finish_warmup(success=True)
                    except (AttributeError, RuntimeError):
                        pass
                    self.connected = True

            def finish(self) -> None:
                """Finalize the warmup spinner, indicating success or failure."""
                try:
                    if not self.connected:
                        self.printer.finish_warmup(success=False)
                        return
                    if self.finish_on_exit:
                        self.printer.finish_warmup(success=True)
                except (AttributeError, RuntimeError):
                    pass

        # Expose on instance for local reuse without changing public API
        self._warmup_cls = _Warmup

    @dataclass
    class _RunContext:
        printer: TerminalPrinter
        viz_sink: Optional[Any]
        transcript: AlgorithmTranscript
        pipeline_done_summary: Optional[Mapping[str, Any]] = None

    @dataclass
    class _ArtifactDownloadContext:
        base_url: str
        job_id: str
        headers: Mapping[str, str]
        deadline: float
        printer: TerminalPrinter
        warm: Any

    def _create_run_context(
        self, visualizer: Optional[Any]
    ) -> "QernelClient._RunContext":
        return QernelClient._RunContext(
            printer=TerminalPrinter(), viz_sink=visualizer, transcript=AlgorithmTranscript()
        )

    def _handle_start_event(self, ctx: "QernelClient._RunContext", message: str) -> None:
        ctx.printer.print_status("", message or "", level="info")
        if ctx.viz_sink is not None:
            try:
                ctx.viz_sink.update_status(message or "", level="info")
            except (AttributeError, RuntimeError):
                pass

    def _print_storage_details_safely(
        self, printer: TerminalPrinter, event: Any
    ) -> None:
        try:
            printer.print_storage_details(
                artifact=getattr(event, "artifact", None),
                details=getattr(event, "details", None),
            )
        except (AttributeError, RuntimeError):
            pass

    def _update_methods_from_status(
        self, ctx: "QernelClient._RunContext", event: Any, stage: str
    ) -> None:
        if stage.startswith("get_name:ok") and event.result is not None:
            ctx.transcript.methods.get_name_result = str(event.result)
        elif stage.startswith("get_type:ok") and event.result is not None:
            ctx.transcript.methods.get_type_result = str(event.result)
        elif stage.startswith("build_circuit:ok"):
            if event.summary is not None:
                ctx.transcript.methods.build_circuit_summary = event.summary
            if event.obj_type is not None:
                ctx.transcript.methods.build_circuit_type = event.obj_type

    def _handle_status_event(self, ctx: "QernelClient._RunContext", event: Any) -> None:
        stage = event.stage or ""
        message = event.message or ""
        level = self._status_level_from_stage(stage)
        full_msg = f"{stage} {message}".strip() if stage else message
        ctx.printer.print_status("", full_msg, level=level)
        if stage.startswith("storage:"):
            self._print_storage_details_safely(ctx.printer, event)
        if ctx.viz_sink is not None:
            try:
                ctx.viz_sink.update_status(full_msg, level=level)
            except (AttributeError, RuntimeError):
                pass
        self._update_methods_from_status(ctx, event, stage)
        if stage.startswith("pipeline:done") and isinstance(event.summary, Mapping):
            ctx.pipeline_done_summary = event.summary

    def _merge_pipeline_summary_into_analysis(
        self, response: Any, pipeline_done_summary: Optional[Mapping[str, Any]]
    ) -> None:
        if pipeline_done_summary is None:
            return
        try:
            analysis = getattr(response, "analysis", None) or {}
            if isinstance(analysis, Mapping):
                merged = dict(analysis)
                sum0 = dict(merged.get("summary") or {})
                sum0.update(dict(pipeline_done_summary))
                merged["summary"] = sum0
                response.analysis = merged
        except (AttributeError, RuntimeError):
            pass

    def _decode_optional_artifacts(self, response: Any) -> None:
        try:
            analysis = getattr(response, "analysis", None) or {}
            _decode_circuit_artifacts_in_place(analysis)
        except (AttributeError, RuntimeError):
            pass

    def _print_and_visualize_result(
        self,
        ctx: "QernelClient._RunContext",
        task_summary: list[dict[str, Any]],
        full_response: Optional[dict[str, Any]],
    ) -> None:
        methods_payload = ctx.transcript.methods
        ctx.printer.print_result_summary(
            class_name=ctx.transcript.class_name,
            class_doc=ctx.transcript.class_doc,
            methods=methods_payload.model_dump(),
        )
        if task_summary:
            try:
                ctx.printer.print_task_summary(task_summary)
            except (AttributeError, RuntimeError):
                pass
        if ctx.viz_sink is not None:
            payload = full_response or {
                "class": ctx.transcript.class_name,
                "class_doc": ctx.transcript.class_doc,
                "methods": ctx.transcript.methods.model_dump(),
            }
            if task_summary:
                payload = dict(payload)
                payload["task_summary"] = task_summary
            self._safe_update_visualizer_with_results(ctx.viz_sink, payload)

    def _handle_result_event(self, ctx: "QernelClient._RunContext", event: Any) -> None:
        if event.response is None:
            return
        # Merge final pipeline summary into analysis
        self._merge_pipeline_summary_into_analysis(event.response, ctx.pipeline_done_summary)
        # Decode artifacts for convenience
        self._decode_optional_artifacts(event.response)
        # Update transcript core fields
        ctx.transcript.response = event.response
        ctx.transcript.methods = event.response.methods
        ctx.transcript.class_name = event.response.class_
        ctx.transcript.class_doc = event.response.class_doc
        # Build task summary from build_circuit doc and analysis
        build_doc = ctx.transcript.methods.build_circuit_doc
        task_summary = _summarize_tasks(build_doc, event.response.analysis)
        # Get full response if available
        full_response: Optional[dict[str, Any]] = None
        try:
            full_response = event.response.model_dump(by_alias=True)
        except (AttributeError, RuntimeError):
            pass
        self._print_and_visualize_result(ctx, task_summary, full_response)

    def _handle_error_event(self, ctx: "QernelClient._RunContext", event: Any) -> None:
        ctx.transcript.ended_reason = "error"
        raise QernelAPIError(
            message=event.message or event.error or "Unknown streaming error",
            transcript=ctx.transcript.to_jsonable(),
        )

    def _mask_api_key(self) -> str:
        api_key = self.config.api_key
        if api_key and len(api_key) >= 8:
            return f"{api_key[:4]}...{api_key[-4:]}"
        if api_key:
            return "[set]"
        return "[missing]"

    def _build_headers(self, accept: str) -> dict[str, str]:
        headers = dict(self.config.get_headers())
        headers["Accept"] = accept
        return headers

    def _serialize_algorithm(self, algorithm_instance: Algorithm) -> str:
        """Serialize an algorithm instance and return base64-encoded string."""
        try:
            serialized_algorithm = cloudpickle.dumps(algorithm_instance)
            encoded_algorithm = base64.b64encode(serialized_algorithm).decode("utf-8")
            return encoded_algorithm
        except (ValueError, TypeError) as e:
            self.logger.error("Algorithm serialization failed: %s", e)
            raise

    def _prepare_stream_payload(
        self,
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Return the JSON payload for streaming requests."""
        encoded_algorithm = self._serialize_algorithm(algorithm_instance)
        payload: dict[str, Any] = {"algorithm_pickle": encoded_algorithm}
        if params is not None:
            # Convert Mapping to a concrete dict for JSON serialization.
            payload["params"] = dict(params)
        return payload

    def _status_level_from_stage(self, stage: str) -> str:
        """Return a status level derived from a stage suffix."""
        if stage.endswith(":ok"):
            return "success"
        if stage.endswith(":err"):
            return "error"
        return "info"

    # --- Small helpers to reduce nesting ----------------------------------

    def _safe_update_visualizer_with_results(
        self, viz_sink: Any, payload: Mapping[str, Any]
    ) -> None:
        try:
            viz_sink.update_with_results(payload)
        except (AttributeError, RuntimeError):
            pass

    def _parse_sse_data_line(
        self, data_str: str, parse_json: bool
    ) -> Optional[Union[dict[str, Any], str]]:
        if not parse_json:
            return None
        try:
            return json.loads(data_str)
        except json.JSONDecodeError:
            return None

    def _connect_sse_with_retry(
        self,
        *,
        url: str,
        json_payload: Mapping[str, Any],
        headers: Mapping[str, str],
        start_time: float,
    ) -> requests.Response:
        backoff = 2.0
        while True:
            elapsed = time.perf_counter() - start_time
            remaining = self.config.stream_timeout - elapsed
            if remaining <= 0:
                raise QernelAPIError("Streaming request timed out while warming up origin")
            response = self._sse_post_once(url, json_payload, headers, remaining)
            if response is not None:
                return response
            sleep_s = min(backoff, max(0.5, remaining))
            time.sleep(sleep_s)
            backoff = min(backoff * 2.0, 10.0)

    def _iter_response_lines(self, response: requests.Response) -> Iterator[str]:
        for line in response.iter_lines(decode_unicode=True):
            if line:
                yield line

    def _maybe_parse_event_line(
        self, line: str, parse_json: bool
    ) -> Optional[Union[str, dict[str, Any]]]:
        if not isinstance(line, str) or not line.startswith("data: "):
            return None
        data_str = line[6:]
        parsed = self._parse_sse_data_line(data_str, parse_json)
        return parsed if parsed is not None else data_str

    def _process_stream_event(
        self,
        ctx: "QernelClient._RunContext",
        handlers: Mapping[str, Any],
        evt: Union[str, dict[str, Any]],
    ) -> bool:
        se = self._validate_or_print_passthrough(evt)
        if se is None:
            return False
        ctx.transcript.add_event(se)
        handler = handlers.get(se.type, lambda _e: None)
        handler(se)
        return se.type == "done"

    def _drain_stream_events(
        self,
        ctx: "QernelClient._RunContext",
        algorithm_instance: Algorithm,
        params: Optional[Mapping[str, Any]],
        handlers: Mapping[str, Any],
    ) -> None:
        for evt in self.stream_events(
            algorithm_instance, params=params, parse_json=True
        ):
            if self._process_stream_event(ctx, handlers, evt):
                return

    def _get_with_retry_until_deadline(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        deadline: float,
        backoff_range: tuple[float, float],
    ) -> requests.Response:
        initial_backoff, max_backoff = backoff_range
        backoff = max(0.5, float(initial_backoff))
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise QernelAPIError("Artifact download timed out while warming up origin")
            per_attempt_timeout = max(min(remaining, max(self.config.timeout, 60)), 1.0)
            response = self._http_get_once(url, headers, per_attempt_timeout)
            if response is not None:
                return response
            sleep_s = min(backoff, max(0.5, remaining))
            time.sleep(sleep_s)
            backoff = min(backoff * 2.0, max_backoff)

    def _deserialize_artifact_content(self, content: bytes) -> Any:
        try:
            return cloudpickle.loads(gzip.decompress(content))
        except (ValueError, TypeError) as exc:
            raise QernelAPIError(f"Artifact deserialize failed: {str(exc)}") from exc

    def _print_get_request_status(self, printer: TerminalPrinter, url: str) -> None:
        try:
            printer.print_status(
                "",
                f"GET {url} (x-api-key={self._mask_api_key()})",
                level="info",
            )
        except (AttributeError, RuntimeError):
            pass

    def _download_and_deserialize_artifact(
        self,
        ctx: "QernelClient._ArtifactDownloadContext",
        name: str,
        is_first: bool,
    ) -> Any:
        url = f"{ctx.base_url}/artifacts/jobs/{ctx.job_id}/artifacts/download/{name}"
        backoff_range = (2.0, 10.0) if is_first else (1.0, 6.0)
        response = self._get_with_retry_until_deadline(
            url=url,
            headers=ctx.headers,
            deadline=ctx.deadline,
            backoff_range=backoff_range,
        )
        ctx.warm.mark_connected()
        self._print_get_request_status(ctx.printer, url)
        return self._deserialize_artifact_content(response.content)

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
        except (RuntimeError, ValueError, TypeError) as e:
            self.logger.error("Failed to serialize algorithm for streaming: %s", e)
            raise

        base_url = (self.config.api_url or "").rstrip("/")
        url = f"{base_url}/stream"
        headers = self._build_headers("text/event-stream")
        self.logger.info(
            "POST %s (stream=True, timeout=%ss)", url, self.config.stream_timeout
        )
        for line in self._post_sse_with_retry(url, payload, headers):
            if not line:
                continue
            maybe_parsed = self._maybe_parse_event_line(line, parse_json)
            yield maybe_parsed if maybe_parsed is not None else line

    def _post_sse_with_retry(
        self, url: str, json_payload: Mapping[str, Any], headers: Mapping[str, str]
    ) -> Iterator[str]:
        """POST to an SSE endpoint with warm-up spinner and retries, yielding lines."""
        tprinter = TerminalPrinter()
        warm = self._warmup_cls(printer=tprinter)
        warm.start()
        try:
            start = time.perf_counter()
            response = self._connect_sse_with_retry(
                url=url,
                json_payload=json_payload,
                headers=headers,
                start_time=start,
            )
            warm.mark_connected()
            yield from self._iter_response_lines(response)
        except QernelAPIError as exc:
            self.logger.error("Streaming request failed: %s", exc.message)
            raise
        finally:
            warm.finish()

    def _sse_post_once(
        self,
        url: str,
        json_payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> Optional[requests.Response]:
        """Attempt a single SSE POST; return response on success, None if retryable.

        Raises QernelAPIError on non-retryable HTTP failures.
        """
        try:
            response = self.session.post(
                url, json=json_payload, headers=headers, stream=True, timeout=timeout
            )
            if response.status_code == 200:
                return response
            if response.status_code in (502, 503, 504):
                return None
            body_preview = response.text[:300]
            msg = f"Streaming request failed: {response.status_code} - {body_preview}"
            raise QernelAPIError(
                message=msg,
                status_code=response.status_code,
                response_text=response.text,
            )
        except requests.exceptions.RequestException:
            return None

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
        yield from self.stream_events(
            algorithm_instance, params=params, parse_json=parse_json
        )

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
        ctx = self._create_run_context(visualizer)

        try:
            handlers = {
                "start": lambda e: self._handle_start_event(ctx, e.message or ""),
                "status": lambda e: self._handle_status_event(ctx, e),
                "error": lambda e: self._handle_error_event(ctx, e),
                "result": lambda e: self._handle_result_event(ctx, e),
                "done": lambda e: self._mark_done(ctx),
            }
            self._drain_stream_events(
                ctx=ctx,
                algorithm_instance=algorithm_instance,
                params=params,
                handlers=handlers,
            )

            # Drain complete; ensure end time is set if not already
            if ctx.transcript.ended_at is None:
                ctx.transcript.ended_at = datetime.utcnow()
            return ctx.transcript

        except QernelAPIError:
            if ctx.transcript.ended_at is None:
                ctx.transcript.ended_at = datetime.utcnow()
            raise
        except (RuntimeError, ValueError, TypeError) as e:
            if ctx.transcript.ended_at is None:
                ctx.transcript.ended_at = datetime.utcnow()
            # Wrap unexpected errors with transcript
            raise QernelAPIError(str(e), transcript=ctx.transcript.to_jsonable()) from e
        finally:
            try:
                ctx.printer.finish()
            except (AttributeError, RuntimeError):
                pass

    def _validate_or_print_passthrough(
        self, evt: Union[str, dict[str, Any]]
    ) -> Optional[StreamEvent]:
        """Return a validated StreamEvent or print passthrough and return None."""
        if isinstance(evt, dict):
            try:
                return StreamEvent.model_validate(evt)
            except (AttributeError, RuntimeError):
                print(evt)
                return None
        print(evt)
        return None

    def _mark_done(self, ctx: "QernelClient._RunContext") -> None:
        ctx.transcript.ended_reason = "done"
        ctx.transcript.ended_at = datetime.utcnow()

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
        except (RuntimeError, ValueError, TypeError):
            algo_name = None
        if not algo_name:
            algo_name = f"{algorithm_instance.__class__.__name__}"

        # If visualizer library is unavailable and none provided, fall back to headless
        if algorithm_visualizer_cls is None and visualizer is None:
            return self.run_stream_with_handler(
                algorithm_instance, params=params, visualizer=None
            )
        vis = visualizer or algorithm_visualizer_cls(
            algorithm_name=str(algo_name)
        )  # type: ignore[call-arg]

        transcript: Optional[AlgorithmTranscript] = None

        def _consume_stream() -> None:
            nonlocal transcript
            try:
                transcript = self.run_stream_with_handler(
                    algorithm_instance, params=params, visualizer=vis
                )
            except (RuntimeError, ValueError, TypeError):
                # Ignore; transcript remains None and will be defaulted
                pass

        # Start the GUI on the main thread; SSE runs in webview's startup worker
        vis.start_and_run(on_start=_consume_stream)

        if transcript is None:
            # Should not happen, but ensure we return a valid object.
            transcript = AlgorithmTranscript()
        return transcript

    def list_job_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        """List available artifacts for a given job.

        Returns a list of objects with at least name/path and size fields,
        as provided by the server.
        """
        base_url = (self.config.api_url or "").rstrip("/")
        url = f"{base_url}/artifacts/jobs/{job_id}/artifacts"
        headers = self._build_headers("application/json")
        masked_key = self._mask_api_key()
        self.logger.info("GET %s (x-api-key=%s)", url, masked_key)
        try:
            response = self.session.get(
                url, headers=headers, timeout=self.config.timeout
            )
            if response.status_code != 200:
                raise QernelAPIError(
                    message=f"Artifact list failed: {response.status_code}",
                    status_code=response.status_code,
                    response_text=response.text,
                )
            data = response.json()
            if isinstance(data, list):
                return data
            # Some servers may wrap in {"artifacts": [...]}
            artifacts = data.get("artifacts") if isinstance(data, Mapping) else None
            return artifacts if isinstance(artifacts, list) else []
        except requests.exceptions.RequestException as e:
            raise QernelAPIError(f"Artifact list request failed: {str(e)}") from e

    def load_artifact(self, job_id: str, artifact_name: str) -> Any:
        """Download and deserialize a gzipped, pickled artifact for a job.

        Uses cloudpickle to reconstruct arbitrary Python objects. Only use with
        trusted servers.
        """
        base_url = (self.config.api_url or "").rstrip("/")
        path = f"/artifacts/jobs/{job_id}/artifacts/download/{artifact_name}"
        url = f"{base_url}{path}"
        headers = self._build_headers("application/octet-stream")
        self.logger.info("GET %s (x-api-key=%s)", url, self._mask_api_key())

        # Mirror streaming warm-up UX: spinner + retry/backoff for cold origins
        tprinter = TerminalPrinter()
        warm = self._warmup_cls(printer=tprinter)
        warm.start()
        deadline = time.perf_counter() + max(
            self.config.stream_timeout, self.config.timeout, 60
        )

        try:
            response = self._get_with_retry_until_deadline(
                url=url,
                headers=headers,
                deadline=deadline,
                backoff_range=(2.0, 10.0),
            )
            warm.mark_connected()
            return self._deserialize_artifact_content(response.content)
        except QernelAPIError as exc:
            # Re-raise after ensuring spinner is finalized below
            raise exc
        finally:
            warm.finish()

    def _http_get_once(
        self, url: str, headers: Mapping[str, str], timeout: float
    ) -> Optional[requests.Response]:
        """Attempt a single GET; return response on success, None if retryable.

        Raises QernelAPIError on non-retryable HTTP failures.
        """
        try:
            response = self.session.get(url, headers=headers, timeout=timeout)
            if response.status_code == 200:
                return response
            if response.status_code in (502, 503, 504):
                return None
            raise QernelAPIError(
                message=f"Artifact download failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
            )
        except requests.exceptions.RequestException:
            return None

    def close(self) -> None:
        """Close underlying HTTP session."""
        try:
            self.session.close()
        except (AttributeError, RuntimeError):
            pass

    def __enter__(self) -> "QernelClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def load_artifacts_sequential(
        self, job_id: str, artifact_names: list[str]
    ) -> dict[str, Any]:
        """Download multiple artifacts sequentially using a single warm-up spinner.

        The first request performs warm-up with spinner + retry/backoff. Subsequent
        requests are issued without re-starting the warm-up spinner, but still
        retry on common transient errors within the remaining timeout window.
        """
        if not artifact_names:
            return {}

        base_url = (self.config.api_url or "").rstrip("/")
        headers = self._build_headers("application/octet-stream")

        printer = TerminalPrinter()
        warm = self._warmup_cls(printer=printer)
        warm.start()
        deadline = time.perf_counter() + max(
            self.config.stream_timeout, self.config.timeout, 60
        )

        results: dict[str, Any] = {}

        try:
            dl_ctx = QernelClient._ArtifactDownloadContext(
                base_url=base_url,
                job_id=job_id,
                headers=headers,
                deadline=deadline,
                printer=printer,
                warm=warm,
            )
            for idx, name in enumerate(artifact_names):
                results[name] = self._download_and_deserialize_artifact(
                    dl_ctx, name, is_first=(idx == 0)
                )

            return results
        except QernelAPIError as exc:
            raise exc
        finally:
            warm.finish()

    def test_connection(self) -> dict[str, Any]:
        """Test the connection to the Qernel API."""
        url = f"{self.config.api_url}/"
        headers = self._build_headers("application/json")
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
                "status": "success" if response.status_code == 200 else "error",
                "message": (
                    "Connection successful"
                    if response.status_code == 200
                    else f"Connection failed with status {response.status_code}"
                ),
                "response": (
                    response.json() if response.status_code == 200 else response.text
                ),
            }
        except requests.exceptions.RequestException as e:
            self.logger.error("Connection failed: %s", e)
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}",
                "response": None,
            }
