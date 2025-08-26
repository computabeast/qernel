"""Simple terminal pretty-printer for Qernel streaming output.

Provides basic, colorized console output for statuses and results.
Designed to be minimal now, but easy to extend.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional


class TerminalPrinter:
    """Pretty printer for terminal output with basic ANSI colors."""

    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "info": "\033[36m",      # cyan
        "success": "\033[32m",   # green
        "warning": "\033[33m",   # yellow
        "error": "\033[31m",     # red
        "title": "\033[35m",    # magenta
        "sub": "\033[90m",      # bright black / gray
    }

    def __init__(self, enable_color: Optional[bool] = None):
        if enable_color is None:
            # Enable color if stdout is a TTY and not explicitly disabled
            enable_color = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
        self.enable_color = enable_color

    def _c(self, text: str, color_key: str) -> str:
        if not self.enable_color:
            return text
        c = self.COLORS.get(color_key, "")
        r = self.COLORS["reset"]
        return f"{c}{text}{r}" if c else text

    def print_header(self, title: str, subtitle: Optional[str] = None) -> None:
        print(self._c(title, "title"))
        if subtitle:
            print(self._c(subtitle, "sub"))

    def print_status(self, stage: str, message: str = "", level: str = "info") -> None:
        level = level.lower() if level else "info"
        level_text = level.upper()
        tag = self._c(f"[{level_text}]", level if level in self.COLORS else "info")
        if stage and message:
            print(f"{tag} {stage} {message}")
        elif stage:
            print(f"{tag} {stage}")
        else:
            print(f"{tag} {message}")

    def print_result_summary(self, *, class_name: Optional[str], class_doc: Optional[str], methods: Dict[str, Any]) -> None:
        print(self._c("\n=== Result ===", "bold"))
        if class_name:
            print(f"Class: {class_name}")
        if class_doc:
            print(f"Doc: {class_doc}")
        name = methods.get("get_name_result")
        typ = methods.get("get_type_result")
        circuit = methods.get("build_circuit_summary")
        if name is not None:
            print(f"Name: {name}")
        if typ is not None:
            print(f"Type: {typ}")
        if circuit is not None:
            print("Circuit (ascii):")
            print(circuit)

    def print_metrics(self, summary: Dict[str, Any]) -> None:
        parts = [f"{k}={v}" for k, v in summary.items() if v is not None]
        if parts:
            print("Metrics:", ", ".join(parts))



