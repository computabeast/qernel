use anyhow::{Context, Result};
use serde_json::json;
use crate::common::network::{default_client, detect_provider, parse_ollama_text, parse_openai_text, ProviderKind, ollama_chat_url, openai_responses_url, preflight_check};

pub fn call_text_model(api_key: &str, model: &str, system: &str, user: &str) -> Result<String> {
    use reqwest::blocking::Client;
    let provider = detect_provider();
    let use_ollama = provider == ProviderKind::Ollama;

    if !use_ollama && api_key.is_empty() { anyhow::bail!("OPENAI_API_KEY is empty"); }
    let client: Client = default_client(300)?;
    preflight_check(&client, provider, model)?;

    if use_ollama {
        // Ollama via OpenAI-compatible Chat Completions API
        let url = ollama_chat_url();
        let messages = vec![
            json!({"role": "system", "content": system}),
            json!({"role": "user", "content": user}),
        ];

        let resp = client
            .post(&url)
            .json(&json!({
                "model": model,
                "messages": messages,
                "stream": false
            }))
            .send()
            .context("send ollama chat request")?;

        let status = resp.status();
        let text = resp.text().unwrap_or_default();
        if !status.is_success() {
            anyhow::bail!("Ollama error {}: {}", status, text);
        }
        let body: serde_json::Value = serde_json::from_str(&text).context("parse ollama json")?;
        if let Some(s) = parse_ollama_text(&body) { return Ok(s); }
        anyhow::bail!("No text in Ollama response")
    } else {
        // OpenAI Responses API (existing behavior)
        let input = vec![
            json!({"role":"system","content":system}),
            json!({"role":"user","content":user}),
        ];

        let resp = client
            .post(&openai_responses_url())
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
        if let Some(s) = parse_openai_text(&body) { return Ok(s); }
        anyhow::bail!("No text in OpenAI response")
    }
}


