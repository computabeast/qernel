"""
Simple terminal pretty-printer for Qernel streaming output (uv-style, clean look).

- Rich for styling + pretty tracebacks (no raw ANSI on normal lines).
- Ephemeral spinner on stderr; final spinner line uses ANSI only for the symbol.
- Left-aligned, compact section dividers.
"""

from __future__ import annotations

import os
import re
import sys
import time
import threading
from typing import Any, Dict, Optional, List

from rich.console import Console
from rich.traceback import install as rich_tb

# Pretty tracebacks to stderr
rich_tb(show_locals=False)

_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_CLEAR_EOL = "\x1b[K"


def _isatty(stream) -> bool:
    try:
        return stream.isatty()
    except Exception:
        return False


def _ansi(code: str, text: str, enable: bool) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if enable else text


class _Spinner:
    """Draw an ephemeral spinner line to stderr with ANSI cursor ops."""

    def __init__(
        self, interval: float = 0.08, colorize: bool = True, show_elapsed: bool = False
    ):
        self.interval = interval
        self.colorize = colorize
        self.show_elapsed = show_elapsed
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._label = ""
        self._frame = 0
        self._t0: Optional[float] = None

    def start(self, label: str) -> None:
        self._label = label
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._t0 = time.time()

    def _run(self) -> None:
        while not self._stop.is_set():
            ch = _SPINNER_FRAMES[self._frame % len(_SPINNER_FRAMES)]
            if self.colorize:
                ch = _ansi("36", ch, True)  # cyan spinner
            if self.show_elapsed and self._t0 is not None:
                elapsed = time.time() - self._t0
                label = f"{self._label} {elapsed:.1f}s"
            else:
                label = self._label
            sys.stderr.write("\r" + f"{ch} {label}" + _CLEAR_EOL)
            sys.stderr.flush()
            self._frame += 1
            time.sleep(self.interval)

    def stop_and_replace(self, replacement_line: str) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.25)
        sys.stderr.write("\r" + replacement_line + _CLEAR_EOL + "\n")
        sys.stderr.flush()

    def stop_and_clear(self) -> None:
        """Stop the spinner and clear the line (no persisted output)."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=0.25)
        sys.stderr.write("\r" + _CLEAR_EOL)
        sys.stderr.flush()


class TerminalPrinter:
    """Pretty printer with Rich + uv-style steps."""

    # Detects "<name>:<suffix>" where suffix ∈ {start, call, ok, err, error, fail, failed}
    _STEP_RE = re.compile(
        r"^\s*(?P<name>.+):(?P<suffix>start|call|ok|err(?:or)?|fail(?:ed)?|skipp(?:ed)?|skipped)\b(?:[:\s]*(?P<rest>.*))?$",
        re.IGNORECASE,
    )

    _LEVEL_STYLE = {
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    }

    _DIV_CHAR = "─"
    _DIV_WIDTH = 28  # short divider, left-aligned

    def __init__(self, enable_color: Optional[bool] = None):
        # Render progress/status to stderr so stdout can be piped/parsed
        self.console = Console(stderr=True, soft_wrap=False, highlight=False)

        # Color on if terminal + NO_COLOR not set (Rich will downgrade if unsupported)
        if enable_color is None:
            enable_color = _isatty(sys.stderr) and os.getenv("NO_COLOR") is None
        self.enable_color = enable_color

        # Spinner only in real TTY and not in CI
        self._ephemeral_ok = self.console.is_terminal and os.getenv("CI") is None

        # Active step/spinner state
        self._active_name: Optional[str] = None
        self._active_label: Optional[str] = None
        self._spinner: Optional[_Spinner] = None
        # Lines to print after a step concludes (avoids mixing with spinner line)
        self._pending_notes: dict[str, list[str]] = {}

    # ---------- helpers ----------

    def _tag(self, level: str) -> str:
        level = (level or "info").lower()
        style = self._LEVEL_STYLE.get(level, "cyan")
        return f"[bold {style}][{level.upper()}][/bold {style}]"

    def _mark_console(self, kind: str) -> str:
        if kind == "success":
            return "[green]✓[/]"
        if kind == "error":
            return "[red]✗[/]"
        if kind == "warning":
            return "[yellow]![/]"
        return "[cyan]•[/]"

    def _mark_ansi(self, kind: str) -> str:
        # Used only for spinner replacement lines (raw writes)
        if kind == "success":
            return _ansi("32", "✓", self.enable_color)  # green
        if kind == "error":
            return _ansi("31", "✗", self.enable_color)  # red
        if kind == "warning":
            return _ansi("33", "!", self.enable_color)  # yellow
        return _ansi("36", "•", self.enable_color)  # cyan

    def _divider(self) -> str:
        return f"[bright_black]{self._DIV_CHAR * self._DIV_WIDTH}[/bright_black]"

    def _section(self, title: str) -> None:
        self.console.print(f"[bold]{title}[/]")
        self.console.print(self._divider())

    def _begin_step(self, name: str, label: str) -> None:
        # If a spinner is already active and we never got an ok/err for it,
        # just clear it (no persisted "continued" noise).
        if self._spinner:
            self._spinner.stop_and_clear()
            self._spinner = None
            self._active_name = None
            self._active_label = None

        self._active_name = name
        self._active_label = label
        # reset pending notes for this step
        if name in self._pending_notes:
            del self._pending_notes[name]
        if self._ephemeral_ok:
            self._spinner = _Spinner(colorize=self.enable_color)
            self._spinner.start(label=label)
        else:
            self.console.print(f"[cyan]{label}[/]")

    def _end_step(
        self, status: str, name: Optional[str], note: Optional[str] = None
    ) -> None:
        note = f" {note}" if note else ""
        label_text = name or (self._active_label or "")

        if self._spinner:
            # Raw write -> use ANSI for the symbol only
            if status == "success":
                line = f"{self._mark_ansi('success')} {label_text}: ok{note}"
            elif status == "error":
                line = f"{self._mark_ansi('error')} {label_text}: failed{note}"
            else:
                line = f"{self._mark_ansi('info')} {label_text}{note}"
            self._spinner.stop_and_replace(line)
            self._spinner = None
        else:
            # Normal path -> Rich markup
            if status == "success":
                self.console.print(
                    f"{self._mark_console('success')} {label_text}: ok{note}"
                )
            elif status == "error":
                self.console.print(
                    f"{self._mark_console('error')} {label_text}: failed{note}"
                )
            else:
                self.console.print(f"{self._mark_console('info')} {label_text}{note}")

        # Print any pending notes captured during spinner
        if name and name in self._pending_notes:
            for line in self._pending_notes.pop(name):
                self.console.print(line)
        self._active_name = None
        self._active_label = None

    def print_header(self, title: str, subtitle: Optional[str] = None) -> None:
        self._section("Result" if title.strip().lower() == "result" else title)
        if subtitle:
            self.console.print(f"[bright_black]{subtitle}[/]")

    def print_status(self, stage: str, message: str = "", level: str = "info") -> None:
        """
        Smart status:
        - "<name>:start|call" -> start spinner
        - "<name>:ok" -> ✓ replace
        - "<name>:(err|error|fail|failed)" -> ✗ replace
        - else -> normal "[LEVEL] ..." line (Rich)
        """
        text = (f"{stage} {message}".strip() if stage else message).strip()

        m = self._STEP_RE.match(text)
        if m:
            name = m.group("name")
            suffix = m.group("suffix").lower()
            rest = (m.group("rest") or "").strip()
            label = f"{name}:{suffix}" + (f" {rest}" if rest else "")
            if suffix in ("start", "call"):
                self._begin_step(name, label)
                return
            if suffix == "ok":
                self._end_step("success", name, note=(rest or None))
                return
            if suffix in ("err", "error", "fail", "failed"):
                self._end_step("error", name, note=(rest or None))
                return
            if suffix in ("skipped", "skipp", "skipped"):
                self._end_step("info", name, note=(rest or None))
                return

        # Storage-specific formatting (status lines that include artifact/details)
        if stage.startswith("storage:"):
            # Normalize levels
            st_level = (level or "info").lower()
            if ":ok" in stage:
                st_level = "success"
            elif ":err" in stage:
                st_level = "error"
            self.console.print(f"{self._mark_console(st_level)} {text}")
            return

        # Plain line via Rich (no raw ANSI)
        if (level or "info").lower() == "info":
            self.console.print(f"{self._mark_console('info')} {text}")
        else:
            tag = self._tag(level)
            self.console.print(f"{tag} {text}")

    def print_result_summary(
        self,
        *,
        class_name: Optional[str],
        class_doc: Optional[str],
        methods: Dict[str, Any],
    ) -> None:
        # One blank line after the debug/status area
        self.console.print()
        # name,type line (bold only name)
        name = methods.get("get_name_result")
        typ = methods.get("get_type_result")
        if name is not None and typ is not None:
            self.console.print(f"[bold]{name}[/], {typ}")
        elif name is not None:
            self.console.print(f"[bold]{name}[/]")
        elif typ is not None:
            self.console.print(str(typ))
        # gray docstrings (class doc bold gray; build_circuit doc normal gray)
        if class_doc:
            self.console.print(f"[bold bright_black]{class_doc}[/]")
        build_doc = methods.get("build_circuit_doc")
        if build_doc:
            self.console.print(f"[bright_black]{build_doc}[/]")
        # ascii circuit with no header
        circuit = methods.get("build_circuit_summary")
        if circuit is not None:
            self.console.print(circuit)

    def print_metrics(self, summary: Dict[str, Any]) -> None:
        parts = [f"{k}={v}" for k, v in summary.items() if v is not None]
        if parts:
            self.console.print("[bold]Metrics:[/] " + ", ".join(parts))

    def print_task_summary(self, tasks: List[Dict[str, Any]]) -> None:
        if not tasks:
            return
        # No section header; keep a single blank line spacer
        self.console.print()
        for t in tasks:
            title = t.get("title", "Task")
            status = (t.get("status") or "info").lower()
            tag = (
                "[bold green][OK][/bold green]"
                if status == "success"
                else "[bold cyan][INFO][/bold cyan]"
            )
            self.console.print(f"{tag} {title}")
            details = t.get("details") or {}
            if isinstance(details, dict) and details:
                for k, v in details.items():
                    self.console.print(f"  • [bold]{k}[/]: {v}")

    def finish(self) -> None:
        """Clean up any active spinner so it doesn't linger."""
        if self._spinner:
            self._spinner.stop_and_clear()
            self._spinner = None
        self._active_name = None
        self._active_label = None

    # ---- Warmup helpers (explicit spinner with elapsed seconds) ----

    def start_warmup(self, label: Optional[str] = None) -> None:
        if self._spinner:
            self._spinner.stop_and_clear()
            self._spinner = None
        # Default label with gray parenthetical hint
        if label is None:
            gray_hint = _ansi(
                "90", "(slower after periods of inactivity)", self.enable_color
            )
            label = f"server warm up: {gray_hint}"
        self._active_name = "warmup"
        self._active_label = label
        if self._ephemeral_ok:
            self._spinner = _Spinner(colorize=self.enable_color, show_elapsed=True)
            self._spinner.start(label=label)
        else:
            self.console.print(f"[cyan]{label}[/]")

    def finish_warmup(self, success: bool = True) -> None:
        if not self._active_name == "warmup":
            return
        # Compose replacement line using ANSI mark like other steps
        symbol = self._mark_ansi("success" if success else "error")
        note = "connected" if success else "failed"
        label_text = self._active_label or "warmup"
        # Avoid double colon if label already includes one
        sep = " " if ":" in label_text else ": "
        line = f"{symbol} {label_text}{sep}{note}"
        if self._spinner:
            self._spinner.stop_and_replace(line)
            self._spinner = None
        else:
            self.console.print(line)
        self._active_name = None
        self._active_label = None

    # ---- Storage detail helpers (for storage:* status lines) ----

    def print_storage_details(
        self, *, artifact: Optional[str], details: Optional[Dict[str, Any]]
    ) -> None:
        """Render storage artifact/details lines in a compact readable form."""
        lines: List[str] = []
        if artifact:
            lines.append(f"{self._mark_console('info')} artifact={artifact}")
        if isinstance(details, dict) and details:
            parts: List[str] = []
            for k in ("bucket", "paths", "size"):
                if k in details:
                    parts.append(f"{k}={details[k]}")
            if not parts:
                parts = [f"{k}={v}" for k, v in details.items()]
            if parts:
                lines.append("  " + ", ".join(parts))

        if not lines:
            return

        # If a spinner is active, defer lines until the step concludes
        if self._spinner and self._active_name:
            self._pending_notes.setdefault(self._active_name, []).extend(lines)
            return

        for line in lines:
            self.console.print(line)
