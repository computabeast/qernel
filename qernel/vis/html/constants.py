"""
HTML template constants for qernel visualization.
"""

# Color scheme (dark theme)
COLORS = {
    "fg": "#e5e7eb",  # Foreground text
    "sub": "#9ca3af",  # Subtitle/secondary text
    "sep": "#374151",  # Separator lines
    "bg": "#222",  # Background
    "circuit_bg": "#0f172a",  # Circuit background
    "info": "#3b82f6",  # Info level color
    "warning": "#f59e0b",  # Warning level color
    "error": "#ef4444",  # Error level color
    "success": "#10b981",  # Success level color
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

# Header section template (subtitle removed)
HEADER_TEMPLATE = """
<div style="font-weight: 700; font-size: 24px; margin-bottom: 16px;">
    {algorithm_name}
</div>"""

# Current status section template (simplified, with link to open debug history)
STATUS_SECTION_TEMPLATE = """
<div style=\"background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px; margin-bottom: 20px;\">
    <div style=\"display:flex; align-items:center; justify-content:space-between; margin-bottom: 8px;\">
        <div style=\"font-weight: 600; font-size: 16px;\">Current Status</div>
        <a href=\"#\" onclick=\"var el=document.getElementById('debug-history'); el && (el.setAttribute('open','open'), el.scrollIntoView(true)); return false;\" style=\"font-size: 12px; color: {sub}; text-decoration: underline;\">Open Debug History</a>
    </div>
    <div style=\"color: {fg}; font-size: 14px;\">{current_status}</div>
</div>"""

# Status history section template (accordion, fixed bottom-right, gray)
STATUS_HISTORY_SECTION_TEMPLATE = """
<div style="position: fixed; bottom: 16px; right: 16px; width: 380px; background: #2b2b2b; color: {fg}; border: 1px solid {sep}; border-radius: 8px; padding: 12px 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); z-index: 9999;">
    <details id="debug-history">
        <summary style="cursor: pointer; display:flex; align-items:center; gap:8px; font-weight: 600; font-size: 14px; color: {sub}; list-style: none;">
            <span style="display:inline-flex; width:16px; height:16px; color:{sub}">
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" width="16" height="16">
                    <path d="M20 8h-3.17l1.59-1.59a1 1 0 10-1.41-1.41L14 8.01V4a1 1 0 10-2 0v4.01L6.99 5.01a1 1 0 10-1.41 1.41L7.17 8H4a1 1 0 100 2h3.59L6 11.59a1 1 0 101.41 1.41L12 8.41l4.59 4.59A1 1 0 0018 13a1 1 0 00.71-1.71L16.41 10H20a1 1 0 100-2z" fill="currentColor"/>
                </svg>
            </span>
            Debug: Status History
        </summary>
        <div style="margin-top: 10px; max-height: 40vh; overflow:auto;">
            {status_updates}
        </div>
    </details>
</div>"""

# Individual status update template
STATUS_UPDATE_TEMPLATE = """
<div style="margin-bottom: 8px; padding: 8px; border-left: 3px solid {level_color}; background: rgba(255,255,255,0.02);">
    <div style="font-size: 12px; color: {sub}; margin-bottom: 2px;">{timestamp}</div>
    <div style="color: {fg}; font-size: 14px;">{message}</div>
</div>"""

# Results section template (accepts raw HTML content)
RESULTS_SECTION_TEMPLATE = """
<div style="background: rgba(255,255,255,0.05); border-radius: 8px; padding: 16px;">
    <div style="font-weight: 600; font-size: 16px; margin-bottom: 12px;">Query Summary</div>
    <div style="color: {fg}; font-size: 14px; line-height: 1.5;">
        {results_content}
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

# Code snippets section template (accordion style)
CODE_SNIPPETS_SECTION_TEMPLATE = """
<div style="margin-top: 20px;">
    <details style="margin-bottom: 12px;">
        <summary style="cursor: pointer; font-weight: 600; font-size: 16px; color: {fg}; padding: 8px 0;">
            Source
        </summary>
        <div style="display: flex; flex-direction: column; gap: 12px; margin-top: 12px;">
            {algorithm_code_snippet}
        </div>
    </details>
</div>"""

# Individual code snippet template (compact)
CODE_SNIPPET_TEMPLATE = """
<div style="background: rgba(0,0,0,0.3); border-radius: 4px; padding: 8px;">
    <div style="font-weight: 500; font-size: 12px; margin-bottom: 6px; color: {sub};">{title}</div>
    <pre style="font-size: 10px; line-height: 1.3; background: {circuit_bg}; border: 1px solid {sep}; border-radius: 3px; padding: 6px; margin: 0; color: {fg}; max-height: 200px; overflow-y: auto; font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace; white-space: pre-wrap; word-wrap: break-word;">{code_content}</pre>
</div>"""
