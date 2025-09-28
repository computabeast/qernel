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
