"""
HTML builder for qernel visualization templates.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .constants import (
    COLORS, BASE_HTML_TEMPLATE, HEADER_TEMPLATE, STATUS_SECTION_TEMPLATE,
    STATUS_HISTORY_SECTION_TEMPLATE, STATUS_UPDATE_TEMPLATE, RESULTS_SECTION_TEMPLATE,
    CIRCUIT_PREVIEW_TEMPLATE, CIRCUIT_IMAGE_TEMPLATE, CIRCUIT_TEXT_TEMPLATE,
    STATS_BADGE_TEMPLATE, CIRCUIT_3D_SECTION_TEMPLATE, CODE_SNIPPETS_SECTION_TEMPLATE,
    CODE_SNIPPET_TEMPLATE
)


class HTMLBuilder:
    """Builder class for creating HTML visualization templates."""
    
    @staticmethod
    def build_combined_view(algorithm_name: str, current_status: str, 
                           status_updates: List[Dict[str, Any]], 
                           final_results: Optional[Dict[str, Any]] = None,
                           algorithm_code: Optional[str] = None,
                           yaml_code: Optional[str] = None) -> str:
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
            algorithm_name=algorithm_name,
            sub=COLORS["sub"]
        )
        
        # Build status section
        status_section = STATUS_SECTION_TEMPLATE.format(
            fg=COLORS["fg"],
            current_status=current_status
        )
        
        # Build status history
        status_updates_html = ""
        for update in status_updates[-10:]:  # Show last 10 updates
            timestamp = update.get('timestamp')
            if timestamp is None:
                timestamp = datetime.now()
            time_str = timestamp.strftime("%H:%M:%S")
            level = update.get('level', 'info')
            message = update.get('message', '')
            
            level_color = COLORS.get(level, COLORS["info"])
            
            status_updates_html += STATUS_UPDATE_TEMPLATE.format(
                level_color=level_color,
                sub=COLORS["sub"],
                fg=COLORS["fg"],
                timestamp=time_str,
                message=message
            )
        
        status_history = STATUS_HISTORY_SECTION_TEMPLATE.format(
            status_updates=status_updates_html
        )
        
        # Build results section if available
        results_section = ""
        if final_results:
            results_content = HTMLBuilder._format_results_content(final_results)
            results_section = RESULTS_SECTION_TEMPLATE.format(
                fg=COLORS["fg"],
                results_content=results_content
            )
        
        # Build code snippets section if available
        code_snippets_section = ""
        if algorithm_code or yaml_code:
            algorithm_snippet = ""
            yaml_snippet = ""
            
            if algorithm_code:
                algorithm_snippet = CODE_SNIPPET_TEMPLATE.format(
                    fg=COLORS["fg"],
                    sub=COLORS["sub"],
                    circuit_bg=COLORS["circuit_bg"],
                    sep=COLORS["sep"],
                    title="Algorithm Code",
                    code_content=HTMLBuilder._escape_html(algorithm_code)
                )
            
            if yaml_code:
                yaml_snippet = CODE_SNIPPET_TEMPLATE.format(
                    fg=COLORS["fg"],
                    sub=COLORS["sub"],
                    circuit_bg=COLORS["circuit_bg"],
                    sep=COLORS["sep"],
                    title="YAML Specification",
                    code_content=HTMLBuilder._escape_html(yaml_code)
                )
            
            code_snippets_section = CODE_SNIPPETS_SECTION_TEMPLATE.format(
                fg=COLORS["fg"],
                algorithm_code_snippet=algorithm_snippet,
                yaml_code_snippet=yaml_snippet
            )
        
        # Combine all sections
        content = header + status_section + status_history + results_section + code_snippets_section
        
        # Build final HTML
        return BASE_HTML_TEMPLATE.format(
            bg=COLORS["bg"],
            fg=COLORS["fg"],
            content=content
        )
    
    @staticmethod
    def build_circuit_preview(title: str, subtitle: str, 
                            circuit_img: str = "", 
                            circuit_text: Optional[str] = None) -> str:
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
                circuit_img=circuit_img,
                circuit_bg=COLORS["circuit_bg"]
            )
        elif circuit_text:
            # Escape HTML characters
            esc = circuit_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            content = CIRCUIT_TEXT_TEMPLATE.format(
                circuit_text=esc,
                circuit_bg=COLORS["circuit_bg"]
            )
        else:
            content = f'<div style="color:{COLORS["sub"]}">(No circuit preview available)</div>'
        
        return CIRCUIT_PREVIEW_TEMPLATE.format(
            title=title,
            subtitle=subtitle,
            content=content,
            sub=COLORS["sub"],
            sep=COLORS["sep"]
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
                sep=COLORS["sep"],
                fg=COLORS["fg"],
                text=stat['text']
            ).replace('style="', f'style="{margin};')
            badges.append(badge)
        
        return ' '.join(badges)
    
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
            raw_html_escaped=raw_html_escaped
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
        lines = []
        
        # Add run ID if available
        if 'run_id' in results:
            lines.append(f"Run ID: {results['run_id']}")
        
        # Add status if available
        if 'status' in results:
            lines.append(f"Status: {results['status']}")
        
        # Add any error messages
        if 'error' in results:
            lines.append(f"Error: {results['error']}")
        
        # Add artifact URLs if available
        if 'artifacts' in results:
            lines.append("Artifacts:")
            for name, url in results['artifacts'].items():
                lines.append(f"  {name}: {url}")
        
        # Add any other relevant information
        for key, value in results.items():
            if key not in ['run_id', 'status', 'error', 'artifacts', 'shots', 'runtime_sec', 
                          'ml_latency_ms', 'L2_noisy', 'L2_ml', 'shots_eff', 'eff_multiplier', 
                          'savings', 'ideal_error']:
                lines.append(f"{key}: {value}")
        
        return "\n".join(lines) if lines else "No additional status information available"
    
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
