"""
HTML builder for qernel visualization templates.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json as _json

from .constants import (
    COLORS,
    BASE_HTML_TEMPLATE,
    HEADER_TEMPLATE,
    STATUS_SECTION_TEMPLATE,
    STATUS_HISTORY_SECTION_TEMPLATE,
    STATUS_UPDATE_TEMPLATE,
    RESULTS_SECTION_TEMPLATE,
    CIRCUIT_PREVIEW_TEMPLATE,
    CIRCUIT_IMAGE_TEMPLATE,
    CIRCUIT_TEXT_TEMPLATE,
    STATS_BADGE_TEMPLATE,
    CIRCUIT_3D_SECTION_TEMPLATE,
    CODE_SNIPPETS_SECTION_TEMPLATE,
    CODE_SNIPPET_TEMPLATE,
)


class HTMLBuilder:
    """Builder class for creating HTML visualization templates."""

    @staticmethod
    def build_combined_view(
        algorithm_name: str,
        current_status: str,
        status_updates: List[Dict[str, Any]],
        final_results: Optional[Dict[str, Any]] = None,
        algorithm_code: Optional[str] = None,
    ) -> str:
        """
        Build the combined HTML view with streaming status and results.

        Args:
            algorithm_name: Name of the algorithm
            current_status: Current status message
            status_updates: List of status update dictionaries
            final_results: Optional final results dictionary

        Returns:
            Complete HTML string
        """
        # Build header
        header = HEADER_TEMPLATE.format(
            algorithm_name=algorithm_name, sub=COLORS["sub"]
        )

        # Build status section
        # Determine current level and time from the latest status update
        if status_updates:
            last = status_updates[-1]
            current_level = (last.get("level") or "info").lower()
            ts = last.get("timestamp") or datetime.now()
        else:
            current_level = "info"
            ts = datetime.now()
        current_time = ts.strftime("%H:%M:%S")
        level_color = COLORS.get(current_level, COLORS["info"])

        status_section = STATUS_SECTION_TEMPLATE.format(
            fg=COLORS["fg"],
            sub=COLORS["sub"],
            sep=COLORS["sep"],
            current_status=current_status,
            current_level=current_level.upper(),
            current_time=current_time,
            level_color=level_color,
        )

        # Build status history
        status_updates_html = ""
        for update in status_updates[-10:]:  # Show last 10 updates
            timestamp = update.get("timestamp")
            if timestamp is None:
                timestamp = datetime.now()
            time_str = timestamp.strftime("%H:%M:%S")
            level = update.get("level", "info")
            message = update.get("message", "")

            level_color = COLORS.get(level, COLORS["info"])

            status_updates_html += STATUS_UPDATE_TEMPLATE.format(
                level_color=level_color,
                sub=COLORS["sub"],
                fg=COLORS["fg"],
                timestamp=time_str,
                message=message,
            )

        status_history = STATUS_HISTORY_SECTION_TEMPLATE.format(
            fg=COLORS["fg"],
            sub=COLORS["sub"],
            sep=COLORS["sep"],
            status_updates=status_updates_html,
        )

        # Build results section if available
        results_section = ""
        if final_results:
            # Tasks first so user intent is clearly addressed
            tasks_section = HTMLBuilder._build_tasks_section(final_results)
            results_content = HTMLBuilder._format_results_content(final_results)
            summary_card = HTMLBuilder._collapsible_card(
                "Query Summary", results_content
            )
            results_section = tasks_section + summary_card

            # Collapsible JSON details card
            json_details = HTMLBuilder._build_json_details(final_results)
            if json_details:
                results_section += json_details

        # Build code snippets section if available
        code_snippets_section = ""
        if algorithm_code:
            algorithm_snippet = CODE_SNIPPET_TEMPLATE.format(
                fg=COLORS["fg"],
                sub=COLORS["sub"],
                circuit_bg=COLORS["circuit_bg"],
                sep=COLORS["sep"],
                title="Algorithm Code",
                code_content=HTMLBuilder._escape_html(algorithm_code),
            )

            code_snippets_section = CODE_SNIPPETS_SECTION_TEMPLATE.format(
                fg=COLORS["fg"], algorithm_code_snippet=algorithm_snippet
            )

        # Combine all sections
        content = (
            header
            + status_section
            + status_history
            + results_section
            + code_snippets_section
        )

        # Build final HTML
        return BASE_HTML_TEMPLATE.format(
            bg=COLORS["bg"], fg=COLORS["fg"], content=content
        )

    @staticmethod
    def build_circuit_preview(
        title: str,
        subtitle: str,
        circuit_img: str = "",
        circuit_text: Optional[str] = None,
    ) -> str:
        """
        Build circuit preview HTML.

        Args:
            title: Preview title
            subtitle: Preview subtitle
            circuit_img: Optional circuit image URL
            circuit_text: Optional circuit text

        Returns:
            Circuit preview HTML string
        """
        if circuit_img:
            content = CIRCUIT_IMAGE_TEMPLATE.format(
                circuit_img=circuit_img, circuit_bg=COLORS["circuit_bg"]
            )
        elif circuit_text:
            # Escape HTML characters
            esc = (
                circuit_text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            content = CIRCUIT_TEXT_TEMPLATE.format(
                circuit_text=esc, circuit_bg=COLORS["circuit_bg"]
            )
        else:
            content = f'<div style="color:{COLORS["sub"]}">(No circuit preview available)</div>'

        return CIRCUIT_PREVIEW_TEMPLATE.format(
            title=title,
            subtitle=subtitle,
            content=content,
            sub=COLORS["sub"],
            sep=COLORS["sep"],
        )

    @staticmethod
    def build_stats_badges(stats_data: List[Dict[str, Any]]) -> str:
        """
        Build stats badges HTML.

        Args:
            stats_data: List of stats dictionaries with 'text' key

        Returns:
            Stats badges HTML string
        """
        badges = []
        for i, stat in enumerate(stats_data):
            margin = "margin-left:8px" if i > 0 else ""
            badge = STATS_BADGE_TEMPLATE.format(
                sep=COLORS["sep"], fg=COLORS["fg"], text=stat["text"]
            ).replace('style="', f'style="{margin};')
            badges.append(badge)

        return " ".join(badges)

    @staticmethod
    def build_circuit_3d_section(circuit_3d_html: str) -> str:
        """
        Build 3D circuit section HTML.

        Args:
            circuit_3d_html: 3D circuit HTML content

        Returns:
            3D circuit section HTML string
        """
        import html as _py_html

        raw_html_escaped = _py_html.escape(circuit_3d_html)

        return CIRCUIT_3D_SECTION_TEMPLATE.format(
            fg=COLORS["fg"],
            sep=COLORS["sep"],
            circuit_bg=COLORS["circuit_bg"],
            sub=COLORS["sub"],
            circuit_3d_html=circuit_3d_html,
            raw_html_escaped=raw_html_escaped,
        )

    @staticmethod
    def _format_results_content(results: Dict[str, Any]) -> str:
        """
        Format results content for display.

        Args:
            results: Results dictionary

        Returns:
            Formatted results string
        """
        class_doc = results.get("class_doc")
        methods = results.get("methods") or {}

        # Extract methods content
        name_result = methods.get("get_name_result")
        type_result = methods.get("get_type_result")
        circuit_text = methods.get("build_circuit_summary")
        build_doc = methods.get("build_circuit_doc")

        parts: List[str] = []
        if class_doc:
            parts.append(
                f"<div style=\"color:{COLORS['sub']};margin-top:4px\">{HTMLBuilder._escape_html(str(class_doc))}</div>"
            )
        if name_result is not None:
            parts.append(
                f'<div style="margin-top:8px"><strong>Name:</strong> {HTMLBuilder._escape_html(str(name_result))}</div>'
            )
        if type_result is not None:
            parts.append(
                f"<div><strong>Type:</strong> {HTMLBuilder._escape_html(str(type_result))}</div>"
            )
        if build_doc:
            parts.append(
                f"<div style=\"margin-top:8px;color:{COLORS['sub']}\">{HTMLBuilder._escape_html(str(build_doc))}</div>"
            )

        # Circuit box
        if circuit_text:
            esc = HTMLBuilder._escape_html(str(circuit_text))
            parts.append(
                f'<div style="margin-top:12px">'
                f'<div style="font-weight:600;font-size:13px;margin-bottom:6px;">Circuit (ASCII)</div>'
                f"<pre style=\"font-size:12px;line-height:1.35;background:{COLORS['circuit_bg']};"
                f"border:1px solid {COLORS['sep']};border-radius:8px;padding:10px;overflow:auto;margin:0;\">{esc}</pre>"
                f"</div>"
            )

        return (
            "".join(parts)
            if parts
            else "<div>No additional status information available</div>"
        )

    @staticmethod
    def _build_json_details(results: Dict[str, Any]) -> str:
        # Build a compact JSON view that merges task_summary (if any) and analysis
        tasks = results.get("task_summary") or []
        analysis = results.get("analysis") or {}
        if not tasks and not analysis:
            return ""
        merged = {"task_summary": tasks} if tasks else {}
        if analysis:
            merged["analysis"] = analysis
        json_str = _json.dumps(merged, indent=2, ensure_ascii=False)
        esc = HTMLBuilder._escape_html(json_str)
        inner = f"<pre style=\"font-size:12px;line-height:1.35;background:{COLORS['circuit_bg']};border:1px solid {COLORS['sep']};border-radius:8px;padding:10px;overflow:auto;margin:0;white-space:pre-wrap\">{esc}</pre>"
        return HTMLBuilder._collapsible_card("Query Details (JSON)", inner)

    @staticmethod
    def _build_tasks_section(results: Dict[str, Any]) -> str:
        tasks = results.get("task_summary") or []
        if not tasks:
            return ""
        rows: List[str] = []
        for t in tasks:
            title = str(t.get("title", "Task"))
            status = (t.get("status") or "info").lower()
            details = t.get("details") or {}
            task_json = t.get("json") or {}
            color = {
                "success": COLORS["success"],
                "error": COLORS["error"],
                "warning": COLORS["warning"],
            }.get(status, COLORS["info"])
            row = (
                f'<div style="display:flex;gap:8px;align-items:flex-start;margin:6px 0;padding:8px;'
                f"border:1px solid {COLORS['sep']};border-radius:6px;background:rgba(255,255,255,0.02)\">"
                f'<span style="display:inline-block;width:8px;height:8px;border-radius:9999px;background:{color}"></span>'
                f'<div style="flex:1"><div style="font-weight:600;font-size:13px">{HTMLBuilder._escape_html(title)}</div>'
            )
            if isinstance(details, dict) and details:
                kv = []
                for k, v in details.items():
                    kv.append(
                        f"<div style=\"font-size:12px;color:{COLORS['sub']}\"><strong>{HTMLBuilder._escape_html(str(k))}:</strong> {HTMLBuilder._escape_html(str(v))}</div>"
                    )
                row += "".join(kv)
            if isinstance(task_json, dict) and task_json:
                j = _json.dumps(task_json, indent=2, ensure_ascii=False)
                esc = HTMLBuilder._escape_html(j)
                row += (
                    f"<details style=\"margin-top:6px\"><summary style=\"cursor:pointer;color:{COLORS['sub']};font-size:12px\">Show result (JSON)</summary>"
                    f"<pre style=\"font-size:11px;line-height:1.3;background:{COLORS['circuit_bg']};border:1px solid {COLORS['sep']};border-radius:6px;padding:8px;overflow:auto;white-space:pre-wrap\">{esc}</pre>"
                    f"</details>"
                )
            row += "</div></div>"
            rows.append(row)
        card = (
            f'<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px; margin-top: 10px;">'
            f'<div style="font-weight:600;font-size:16px;margin-bottom:8px">Tasks</div>'
            f"{''.join(rows)}"
            f"</div>"
        )
        return card

    @staticmethod
    def _collapsible_card(title: str, inner_html: str) -> str:
        """Render a generic collapsible card with a title and HTML content."""
        return (
            f'<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px; margin-top: 16px;">'
            f"<details>"
            f"<summary style=\"cursor:pointer;font-weight:600;font-size:16px;color:{COLORS['fg']}\">{HTMLBuilder._escape_html(title)}</summary>"
            f"<div style=\"margin-top:10px;color:{COLORS['fg']}\">{inner_html}</div>"
            f"</details>"
            f"</div>"
        )

    @staticmethod
    def _escape_html(text: str) -> str:
        """
        Escape HTML characters in text.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
