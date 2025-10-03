use anyhow::{Context, Result};
use serde_json::json;

pub fn call_text_model(api_key: &str, model: &str, system: &str, user: &str) -> Result<String> {
    use reqwest::blocking::Client;
    if api_key.is_empty() { anyhow::bail!("OPENAI_API_KEY is empty"); }
    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(300))
        .build()
        .context("create http client")?;

    // Use Responses API for consistency with existing code
    let input = vec![
        json!({"role":"system","content":system}),
        json!({"role":"user","content":user}),
    ];

    let resp = client
        .post("https://api.openai.com/v1/responses")
        .bearer_auth(api_key)
        .json(&json!({
            "model": model,
            "input": input,
            "parallel_tool_calls": false
        }))
        .send()
        .context("send openai request")?;

    let status = resp.status();
    let text = resp.text().unwrap_or_default();
    if !status.is_success() {
        anyhow::bail!("OpenAI error {}: {}", status, text);
    }
    let body: serde_json::Value = serde_json::from_str(&text).context("parse openai json")?;

    // Prefer output_text, else join message content
    if let Some(s) = body.get("output_text").and_then(|v| v.as_str()) {
        return Ok(s.to_string());
    }
    if let Some(arr) = body.get("output").and_then(|v| v.as_array()) {
        // Try to concatenate text parts
        let mut buf = String::new();
        for item in arr {
            if item.get("type").and_then(|v| v.as_str()) == Some("message") {
                if let Some(parts) = item.get("content").and_then(|v| v.as_array()) {
                    for p in parts {
                        if let Some(t) = p.get("text").and_then(|t| t.as_str()) { buf.push_str(t); }
                    }
                }
            }
        }
        if !buf.is_empty() { return Ok(buf); }
    }
    anyhow::bail!("No text in OpenAI response")
}


