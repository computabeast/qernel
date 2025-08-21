from __future__ import annotations

def base_container(inner_html: str) -> str:
    fg = "#e5e7eb"
    bg = "#222"
    font_stack = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,'Apple Color Emoji','Segoe UI Emoji'"
    return (
        "<!doctype html>\n"
        "<html>\n<head>\n<meta charset=\"utf-8\"/>\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"/>\n"
        f"<style>html,body{{margin:0;padding:0;width:100%;height:100%;background:{bg};color:{fg};font-family:{font_stack}}}"
        "*,*::before,*::after{box-sizing:border-box}"
        "img{max-width:100%;height:auto;display:block}"
        "</style>\n</head>\n<body>\n"
        f"<div style=\"width:100%;min-height:100%;overflow-y:auto;overflow-x:hidden;padding:8px 10px;\">{inner_html}</div>\n"
        "</body>\n</html>"
    )


def section_divider() -> str:
    sep = "#374151"
    return f'<div style="height:1px;background:{sep};opacity:0.5;margin:10px 0"></div>'


