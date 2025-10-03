use serde::{Deserialize, Serialize};
use anyhow::{Context, Result};

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct Config {
    pub token: Option<String>,
    pub default_remote: Option<String>,
    pub default_server: Option<String>,
    /// Optional OpenAI API key for prototyping features
    pub openai_api_key: Option<String>,
}

pub fn load_config() -> Result<Config> {
    let cfg: Config = confy::load("qernel", None).context("failed to load config")?;
    Ok(cfg)
}

pub fn save_config(cfg: &Config) -> Result<()> {
    confy::store("qernel", None, cfg).context("failed to save config")?;
    Ok(())
}

use supports_color::Stream;
use owo_colors::OwoColorize;

pub fn color_enabled_stdout() -> bool {
    supports_color::on(Stream::Stdout).is_some()
}

pub fn sym_check(enabled: bool) -> String {
    if enabled { format!("{}", "✔".green().bold()) } else { "✔".to_string() }
}

pub fn sym_cross(enabled: bool) -> String {
    if enabled { format!("{}", "✖".red().bold()) } else { "x".to_string() }
}

pub fn sym_question(enabled: bool) -> String {
    if enabled { format!("{}", "?".cyan().bold()) } else { "?".to_string() }
}

pub fn sym_gear(enabled: bool) -> String {
    if enabled { format!("{}", "⚙".blue().bold()) } else { "⚙".to_string() }
}

/// Resolve an OpenAI API key from environment or stored config
pub fn get_openai_api_key_from_env_or_config() -> Option<String> {
    if let Ok(k) = std::env::var("OPENAI_API_KEY") {
        let k = k.trim().to_string();
        if !k.is_empty() {
            return Some(k);
        }
    }
    if let Ok(cfg) = load_config() {
        if let Some(k) = cfg.openai_api_key.as_ref() {
            if !k.trim().is_empty() {
                return Some(k.trim().to_string());
            }
        }
    }
    None
}

// Ensure the current process has OPENAI_API_KEY set. Returns true if set via config.
// Note: In Rust 2024, mutating process env at runtime is unsafe; callers should
// resolve the key and pass it explicitly instead of exporting.
/// Persist an OpenAI API key into the local config (not committed to git)
pub fn set_openai_api_key_in_config(secret: &str) -> Result<()> {
    let mut cfg = load_config().unwrap_or_default();
    cfg.openai_api_key = Some(secret.trim().to_string());
    save_config(&cfg)
}

/// Remove any stored OpenAI API key from the local config
pub fn unset_openai_api_key_in_config() -> Result<()> {
    let mut cfg = load_config().unwrap_or_default();
    cfg.openai_api_key = None;
    save_config(&cfg)
}



