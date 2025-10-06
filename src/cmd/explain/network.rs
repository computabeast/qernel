use anyhow::{Context, Result};
use serde_json::json;
use crate::common::network::{default_client, detect_provider, parse_ollama_text, parse_model_text, ProviderKind, ollama_chat_url, qernel_model_url, preflight_check};
use crate::util::get_qernel_pat_from_env_or_config;

pub fn call_text_model(api_key: &str, model: &str, system: &str, user: &str) -> Result<String> {
    use reqwest::blocking::Client;
    let provider = detect_provider();
    let use_ollama = provider == ProviderKind::Ollama;
    let use_qernel = provider == ProviderKind::Qernel;

    if !(use_ollama || use_qernel) && api_key.is_empty() { anyhow::bail!("OPENAI_API_KEY is empty"); }
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
    } else if use_qernel {
        // Qernel model endpoint: minimal Responses-like payload
        let input = vec![
            json!({"role":"system","content":system}),
            json!({"role":"user","content":user}),
        ];
        let url = qernel_model_url();
        let mut req = client.post(&url);
        if let Some(pat) = get_qernel_pat_from_env_or_config() {
            req = req.bearer_auth(pat);
        }
        let resp = req
            .json(&json!({
                "model": model,
                "input": input
            }))
            .send()
            .context("send qernel request")?;

        let status = resp.status();
        let text = resp.text().unwrap_or_default();
        if !status.is_success() {
            anyhow::bail!("Qernel error {}: {}", status, text);
        }
        let body: serde_json::Value = serde_json::from_str(&text).context("parse qernel json")?;
        if let Some(s) = parse_model_text(&body) { return Ok(s); }
        anyhow::bail!("No text in Qernel response")
    } else {
        // OpenAI Responses API (existing behavior)
        let input = vec![
            json!({"role":"system","content":system}),
            json!({"role":"user","content":user}),
        ];

        // Default path: Qernel Responses-compatible endpoint
        let url = qernel_model_url();
        let resp = client
            .post(&url)
            .json(&json!({
                "model": model,
                "input": input,
                "parallel_tool_calls": false
            }))
            .send()
            .context("send qernel request")?;

        let status = resp.status();
        let text = resp.text().unwrap_or_default();
        if !status.is_success() {
            anyhow::bail!("Qernel error {}: {}", status, text);
        }
        let body: serde_json::Value = serde_json::from_str(&text).context("parse qernel json")?;
        if let Some(s) = parse_model_text(&body) { return Ok(s); }
        anyhow::bail!("No text in Qernel response")
    }
}


