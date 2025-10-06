use anyhow::{Context, Result};
use reqwest::blocking::Client;
use serde_json::Value;
use std::env;
use crate::util::{load_config, get_qernel_pat_from_env_or_config};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProviderKind { Qernel, Ollama }

pub fn detect_provider() -> ProviderKind {
    let env_pick = env::var("QERNEL_PROVIDER").unwrap_or_default().to_lowercase();
    if env_pick == "ollama" { return ProviderKind::Ollama; }
    if env_pick == "qernel" { return ProviderKind::Qernel; }
    if let Ok(cfg) = load_config() {
        if let Some(p) = cfg.provider.as_deref() {
            if p.eq_ignore_ascii_case("ollama") { return ProviderKind::Ollama; }
            if p.eq_ignore_ascii_case("qernel") { return ProviderKind::Qernel; }
            return ProviderKind::Qernel;
        }
    }
    ProviderKind::Qernel
}

pub fn default_client(timeout_secs: u64) -> Result<Client> {
    Client::builder()
        .timeout(std::time::Duration::from_secs(timeout_secs))
        .build()
        .context("create http client")
}

pub fn qernel_model_url() -> String {
    "".to_string() // Will need to fill this with the server URL when ready
}

pub fn ollama_chat_url() -> String {
    let base = env::var("OLLAMA_BASE_URL").ok().filter(|s| !s.trim().is_empty()).or_else(|| {
        load_config().ok().and_then(|c| c.ollama_base_url)
    }).unwrap_or_else(|| "http://localhost:11434/v1".to_string());
    format!("{}/chat/completions", base.trim_end_matches('/'))
}

pub fn parse_model_text(body: &Value) -> Option<String> {
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
/// - For Qernel: verifies the endpoint is reachable.
/// - For Ollama: verifies the chat endpoint is reachable and the model exists.
pub fn preflight_check(client: &Client, provider: ProviderKind, model: &str) -> Result<()> {
    match provider {
        ProviderKind::Qernel => {
            // Verify the local/remote qernel model endpoint is reachable.
            let url = qernel_model_url();
            let mut req = client.post(&url);
            if let Some(pat) = get_qernel_pat_from_env_or_config() {
                req = req.bearer_auth(pat);
            }
            let resp = req
                .json(&serde_json::json!({
                    "model": model,
                    "input": [{"role":"system","content":"ping"}],
                    "max_output_tokens": 16
                }))
                .send()
                .context("qernel preflight request")?;
            if !resp.status().is_success() {
                let status = resp.status();
                let text = resp.text().unwrap_or_default();
                anyhow::bail!("Qernel preflight failed: {} {}", status, text);
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


