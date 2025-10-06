use anyhow::Result;
use std::env;

/// Open a native window and render a simple HTML string.
pub fn handle_see(url: Option<String>) -> Result<()> {
    // Default to the Qernel Zoo unless overridden by --url or env
    let target = url.unwrap_or_else(|| env::var("QERNEL_ZOO_URL").unwrap_or_else(|_| "https://qernelzoo.com".to_string()));

    // Simple in-webview loading HTML that redirects to target URL
    let loading = format!(r#"<!doctype html><meta charset='utf-8'>
<title>Loading…</title>
<style>
  html,body{{height:100%;margin:0}} body{{display:grid;place-items:center;background:#0b0b0c;color:#e6e6e6;font:16px system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}}
  .spinner{{width:48px;height:48px;border:4px solid #444;border-top-color:#8b5cf6;border-radius:50%;animation:spin 1s linear infinite;margin:16px auto}}
  @keyframes spin{{to{{transform:rotate(360deg)}}}}
  .box{{text-align:center;max-width:420px;padding:24px 28px;border-radius:12px;background:#151517;border:1px solid #232326}}
</style>
<div class='box'>
  <div class='spinner'></div>
  <div>Opening the Qernel Zoo…</div>
</div>
<script>setTimeout(function(){{location.href = {url:?};}}, 10);</script>
"#, url=target);

    // Show a very quick loading page, then navigate
    // Note: WRY cannot switch page contents after build; we load HTML then change location.
    qernel_vision::open_html(&loading)
}


