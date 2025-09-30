use serde::{Deserialize, Serialize};
use anyhow::{Context, Result};

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct Config {
    pub token: Option<String>,
    pub default_remote: Option<String>,
    pub default_server: Option<String>,
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

