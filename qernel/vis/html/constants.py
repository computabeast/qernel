"""
HTML template constants for qernel visualization.
"""

# Color scheme (dark theme)
COLORS = {
    "fg": "#e5e7eb",      # Foreground text
    "sub": "#9ca3af",     # Subtitle/secondary text
    "sep": "#374151",     # Separator lines
    "bg": "#222",         # Background
    "circuit_bg": "#0f172a",  # Circuit background
    "info": "#3b82f6",    # Info level color
    "warning": "#f59e0b", # Warning level color
    "error": "#ef4444",   # Error level color
    "success": "#10b981", # Success level color
}

# Base HTML template
BASE_HTML_TEMPLATE = """<!doctype html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>
        html,body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background: {bg};
            color: {fg};
            font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
        }}
        *,*::before,*::after {{ box-sizing: border-box; }}
    </style>
</head>
<body>
    <div style="width: 100%; min-height: 100%; padding: 20px;">
        {content}
    </div>
</body>
</html>"""

# Header section template
HEADER_TEMPLATE = """
<div style="font-weight: 700; font-size: 24px; margin-bottom: 8px;">
    {algorithm_name}
</div>
<div style="font-size: 14px; color: {sub}; margin-bottom: 20px;">
    Algorithm Execution Monitor
</div>"""

# Current status section template
STATUS_SECTION_TEMPLATE = """
<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
    <div style="font-weight: 600; font-size: 16px; margin-bottom: 8px;">Current Status</div>
    <div style="color: {fg}; font-size: 14px;">{current_status}</div>
</div>"""

# Status history section template
STATUS_HISTORY_SECTION_TEMPLATE = """
<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
    <div style="font-weight: 600; font-size: 16px; margin-bottom: 12px;">Status History</div>
    {status_updates}
</div>"""

# Individual status update template
STATUS_UPDATE_TEMPLATE = """
<div style="margin-bottom: 8px; padding: 8px; border-left: 3px solid {level_color}; background: rgba(255,255,255,0.02);">
    <div style="font-size: 12px; color: {sub}; margin-bottom: 2px;">{timestamp}</div>
    <div style="color: {fg}; font-size: 14px;">{message}</div>
</div>"""

# Results section template
RESULTS_SECTION_TEMPLATE = """
<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px;">
    <div style="font-weight: 600; font-size: 16px; margin-bottom: 12px;">Execution Results</div>
    <div style="color: {fg}; font-size: 14px; line-height: 1.5;">
        <pre style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 6px; overflow-x: auto; margin: 0;">{results_content}</pre>
    </div>
</div>"""

# Circuit preview template
CIRCUIT_PREVIEW_TEMPLATE = """
<div style="font-weight:700;font-size:15px;margin-bottom:2px;">{title}</div>
<div style="font-size:12px;color:{sub};margin-bottom:8px;">{subtitle}</div>
<div>{content}</div>
<div style="height:1px;background:{sep};opacity:0.5;margin:10px 0 0 0"></div>"""

# Circuit image template
CIRCUIT_IMAGE_TEMPLATE = """
<img src="{circuit_img}" style="display:block;max-width:100%;height:auto;border:none;border-radius:0;background:{circuit_bg};"/>"""

# Circuit text template
CIRCUIT_TEXT_TEMPLATE = """
<pre style="font-size:12px;line-height:1.35;background:{circuit_bg};border:none;border-radius:8px;padding:10px;overflow:auto;margin:0;color:inherit">{circuit_text}</pre>"""

# Stats badges template
STATS_BADGE_TEMPLATE = """
<span style="display:inline-block;padding:2px 6px;border:1px solid {sep};border-radius:9999px;background:transparent;font-size:12px;color:{fg};opacity:.9">{text}</span>"""

# 3D circuit section template
CIRCUIT_3D_SECTION_TEMPLATE = """
<div style="margin-top:10px">
    <div style="font-weight:600;font-size:13px;margin-bottom:6px;color:{fg}">3D Circuit Visualization</div>
    <div style="border:1px solid {sep};border-radius:8px;padding:0;overflow:hidden;background:{circuit_bg};width:100%;height:60vh;min-height:400px;max-height:600px;">
        <div style="width:100%;height:100%;overflow:hidden;">
            {circuit_3d_html}
        </div>
    </div>
    <details style="margin-top:8px">
        <summary style="cursor:pointer;color:{sub};font-size:12px">Show raw HTML (for verification)</summary>
        <pre style="font-size:11px;line-height:1.3;background:{circuit_bg};border:none;border-radius:8px;padding:10px;overflow:auto;color:inherit;max-height:300px;overflow-y:auto">{raw_html_escaped}</pre>
    </details>
</div>
<div style="height:1px;background:{sep};opacity:0.5;margin:10px 0"></div>"""
