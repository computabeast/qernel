from __future__ import annotations
from typing import Optional, Sequence, Dict, Any

from .html import HTMLBuilder


def render_circuit_preview_html(*, title: str, subtitle: str, content_html: str) -> str:
    """Render circuit preview HTML using the HTML builder."""
    return HTMLBuilder.build_circuit_preview(title, subtitle, circuit_text=content_html)


def render_bubble_html(*,
                       title: str,
                       subtitle: str,
                       circuit_html: str,
                       stats_html: str,
                       metrics_html: str,
                       charts_html: str,
                       footer_html: str) -> str:
    """Render bubble HTML using the HTML builder."""
    # This function is kept for backward compatibility but simplified
    from .html.constants import BASE_HTML_TEMPLATE, COLORS
    
    inner = f"""
      <div style="font-weight:700;font-size:15px;margin-bottom:2px;">{title}</div>
      <div style="font-size:12px;color:{COLORS['sub']};margin-bottom:6px">{subtitle}</div>
      {circuit_html}
      {stats_html}
      {metrics_html}
      {charts_html}
      {footer_html}
    """.strip()
    
    return BASE_HTML_TEMPLATE.format(
        bg=COLORS["bg"],
        fg=COLORS["fg"],
        content=inner
    )


def render_circuit_preview(*, title: str, subtitle: str, style_max_width_px: int,
                           circuit_img: str = "", circuit_text: Optional[str] = None) -> str:
    """Render circuit preview using the HTML builder."""
    return HTMLBuilder.build_circuit_preview(title, subtitle, circuit_img, circuit_text)


def render_bubble(*, shots: int, runtime_sec: float, ml_latency_ms: float,
                  L2_noisy: Optional[float], L2_ml: Optional[float],
                  shots_eff: Optional[float], eff_multiplier: Optional[float],
                  savings: Optional[float], show_circuit: bool, circuit_img: str,
                  title: str, subtitle: str, style_max_width_px: int,
                  ideal_error: Optional[str], circuit_text: Optional[str] = None,
                  ez_noisy: Optional[object] = None,
                  ez_ml: Optional[object] = None,
                  ez_ideal: Optional[object] = None,
                  counts: Optional[dict] = None,
                  circuit_3d_html: Optional[str] = None) -> str:
    """Render bubble visualization using the HTML builder."""
    # This function is kept for backward compatibility but simplified
    from .html.constants import BASE_HTML_TEMPLATE, COLORS
    
    # Build stats badges
    stats_data = [
        {'text': f"Shots: {shots:,}"},
        {'text': f"Runtime: {runtime_sec:.3f}s"},
        {'text': f"ML: {ml_latency_ms:.2f} ms"}
    ]
    stats_html = HTMLBuilder.build_stats_badges(stats_data)
    
    # Build circuit section
    circuit_html = ""
    if show_circuit:
        if circuit_img:
            circuit_html = HTMLBuilder.build_circuit_preview(title, subtitle, circuit_img)
        elif circuit_text:
            circuit_html = HTMLBuilder.build_circuit_preview(title, subtitle, circuit_text=circuit_text)
    
    # Build 3D circuit section
    circuit_3d_section = ""
    if circuit_3d_html:
        circuit_3d_section = HTMLBuilder.build_circuit_3d_section(circuit_3d_html)
    
    # Build metrics lines
    metrics_html = ""
    if L2_noisy is not None and L2_ml is not None:
        metrics_html += f'<div style="margin-top:6px;color:{COLORS["fg"]};opacity:.85;font-size:12px"><b>L2 vs ideal (noisy):</b> {L2_noisy:.4f} &nbsp; | &nbsp; <b>ML:</b> {L2_ml:.4f}</div>'
    
    if shots_eff:
        metrics_html += f'<div style="color:{COLORS["fg"]};opacity:.85;font-size:12px"><b>Effective shots to match ML:</b> ~{int(shots_eff):,} (×{eff_multiplier:.1f})</div>'
    
    if ideal_error:
        metrics_html += f'<div style="color:{COLORS["sub"]};font-size:11px;margin-top:8px">{ideal_error}</div>'
    
    # Combine all sections
    inner = f"""
      <div style="font-weight:700;font-size:15px;margin-bottom:2px;">{title}</div>
      <div style="font-size:12px;color:{COLORS['sub']};margin-bottom:6px">{subtitle}</div>
      {circuit_html}
      {circuit_3d_section}
      <div style="font-size:12px;color:{COLORS['fg']};opacity:.85;margin:6px 0 6px">{stats_html}</div>
      {metrics_html}
    """.strip()
    
    return BASE_HTML_TEMPLATE.format(
        bg=COLORS["bg"],
        fg=COLORS["fg"],
        content=inner
    )


