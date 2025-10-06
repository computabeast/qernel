use anyhow::Result;

/// Open a native window and render a simple HTML string.
pub fn handle_see() -> Result<()> {
    // Minimal Hello World HTML
    let html = r#"<!doctype html><meta charset=\"utf-8\">
<title>qernel viewer</title>
<style>body{font-family:system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Helvetica,Arial,sans-serif;margin:40px}</style>
<h1>Hello world</h1>
<p>qernel vision (macOS) demo</p>"#;

    qernel_vision::open_html(html)
}


