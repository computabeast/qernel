use anyhow::{Context, Result};
use reqwest::blocking::Client;
use serde_json::Value;
use std::env;
use crate::util::load_config;
use crate::util::get_openai_api_key_from_env_or_config;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProviderKind {
    OpenAI,
    Ollama,
}

pub fn detect_provider() -> ProviderKind {
    let env_pick = env::var("QERNEL_PROVIDER").unwrap_or_default().to_lowercase();
    if env_pick == "ollama" { return ProviderKind::Ollama; }
    if env_pick == "openai" { return ProviderKind::OpenAI; }
    if let Ok(cfg) = load_config() {
        if let Some(p) = cfg.provider.as_deref() {
            return if p.eq_ignore_ascii_case("ollama") { ProviderKind::Ollama } else { ProviderKind::OpenAI };
        }
    }
    ProviderKind::OpenAI
}

pub fn default_client(timeout_secs: u64) -> Result<Client> {
    Client::builder()
        .timeout(std::time::Duration::from_secs(timeout_secs))
        .build()
        .context("create http client")
}

pub fn openai_responses_url() -> String {
    "https://api.openai.com/v1/responses".to_string()
}

pub fn ollama_chat_url() -> String {
    let base = env::var("OLLAMA_BASE_URL").ok().filter(|s| !s.trim().is_empty()).or_else(|| {
        load_config().ok().and_then(|c| c.ollama_base_url)
    }).unwrap_or_else(|| "http://localhost:11434/v1".to_string());
    format!("{}/chat/completions", base.trim_end_matches('/'))
}

pub fn parse_openai_text(body: &Value) -> Option<String> {
    if let Some(s) = body.get("output_text").and_then(|v| v.as_str()) {
        return Some(s.to_string());
    }
    if let Some(arr) = body.get("output").and_then(|v| v.as_array()) {
        let mut buf = String::new();
        for item in arr {
            if item.get("type").and_then(|v| v.as_str()) == Some("message") {
                if let Some(parts) = item.get("content").and_then(|v| v.as_array()) {
                    for p in parts {
                        if let Some(t) = p.get("text").and_then(|t| t.as_str()) {
                            buf.push_str(t);
                        }
                    }
                }
            }
        }
        if !buf.is_empty() {
            return Some(buf);
        }
    }
    None
}

pub fn parse_ollama_text(body: &Value) -> Option<String> {
    body.get("choices")
        .and_then(|v| v.as_array())
        .and_then(|arr| arr.get(0))
        .and_then(|c| c.get("message"))
        .and_then(|m| m.get("content"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
}

/// Preflight check to validate the current provider configuration.
/// - For OpenAI: verifies an API key exists and a simple request schema is accepted.
/// - For Ollama: verifies the chat endpoint is reachable and the model exists.
pub fn preflight_check(client: &Client, provider: ProviderKind, model: &str) -> Result<()> {
    match provider {
        ProviderKind::OpenAI => {
            if get_openai_api_key_from_env_or_config().is_none() {
                anyhow::bail!("OPENAI_API_KEY is missing. Set it via env or 'qernel auth --set-openai-key'.");
            }
            // Minimal schema poke (no request if not desired). We'll do a lightweight HEAD-equivalent via small POST.
            let resp = client
                .post(&openai_responses_url())
                .bearer_auth(get_openai_api_key_from_env_or_config().unwrap())
                .json(&serde_json::json!({
                    "model": model,
                    "input": [{"role":"system","content":"ping"}],
                    "max_output_tokens": 1
                }))
                .send()
                .context("openai preflight request")?;
            if resp.status().is_client_error() || resp.status().is_server_error() {
                let status = resp.status();
                let text = resp.text().unwrap_or_default();
                anyhow::bail!("OpenAI preflight failed: {} {}", status, text);
            }
            Ok(())
        }
        ProviderKind::Ollama => {
            // Verify endpoint and model availability
            let url = ollama_chat_url();
            let resp = client
                .post(&url)
                .json(&serde_json::json!({
                    "model": model,
                    "messages": [{"role":"system","content":"ping"},{"role":"user","content":"ping"}],
                    "stream": false,
                    "max_tokens": 1
                }))
                .send()
                .context("ollama preflight request")?;
            if !resp.status().is_success() {
                let status = resp.status();
                let text = resp.text().unwrap_or_default();
                anyhow::bail!("Ollama preflight failed: {} {}", status, text);
            }
            Ok(())
        }
    }
}


