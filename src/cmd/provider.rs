use anyhow::Result;
use clap::Args;
use crate::util::{load_config, save_config, Config, get_openai_api_key_from_env_or_config, sym_check, sym_question, color_enabled_stdout};

#[derive(Args)]
pub struct ProviderCmd {
    /// Show current provider configuration
    #[arg(long)]
    pub show: bool,

    /// List available providers
    #[arg(long)]
    pub list: bool,

    /// Run a preflight check for the current or specified model
    #[arg(long)]
    pub check: bool,
    /// Optional model to check (defaults to current CLI-provided model elsewhere)
    #[arg(long)]
    pub model: Option<String>,

    /// Set provider: openai | ollama
    #[arg(long)]
    pub set: Option<String>,

    /// Set Ollama base URL (e.g., http://localhost:11434/v1)
    #[arg(long)]
    pub base_url: Option<String>,

    /// Set model for a specific command: prototype | explain
    #[arg(long)]
    pub set_for_cmd: Option<String>,
    /// Positional model argument when using --set-for-cmd
    pub cmd_model: Option<String>,
}

pub fn handle_provider(cmd: ProviderCmd) -> Result<()> {
    let mut cfg: Config = load_config().unwrap_or_default();
    let ce = color_enabled_stdout();
    if cmd.list {
        println!("openai");
        println!("ollama");
        return Ok(());
    }
    if cmd.check {
        use reqwest::blocking::Client;
        use crate::common::network::{default_client, detect_provider, preflight_check};
        let model = cmd.model.as_deref().unwrap_or("codex-mini-latest");
        let client: Client = default_client(15)?;
        let provider = detect_provider();
        preflight_check(&client, provider, model)?;
        println!("Preflight passed for provider and model '{}'.", model);
        return Ok(());
    }

    if let Some(cmd_name) = cmd.set_for_cmd.as_deref() {
        let model = cmd.cmd_model.as_deref().unwrap_or("");
        if model.is_empty() { anyhow::bail!("MODEL argument is required: qernel provider --set-for-cmd <prototype|explain> <MODEL>"); }
        // Update user-level qernel defaults (not project YAML)
        let mut defaults = load_config().unwrap_or_default();
        match cmd_name.to_lowercase().as_str() {
            "prototype" => defaults.default_prototype_model = Some(model.to_string()),
            "explain" => defaults.default_explain_model = Some(model.to_string()),
            _ => anyhow::bail!("invalid --set-for-cmd '{}': expected 'prototype' or 'explain'", cmd_name),
        }
        save_config(&defaults)?;
        println!("Updated default {} model to '{}' in qernel config.", cmd_name, model);
        return Ok(());
    }
    let show_mode = cmd.show || (cmd.set.is_none() && cmd.base_url.is_none());

    if show_mode {
        println!("Provider: {}", cfg.provider.as_deref().unwrap_or("openai"));
        println!("Ollama_base_url: {}", cfg.ollama_base_url.as_deref().unwrap_or("(unset, default http://localhost:11434/v1)"));

        // Show command-model mapping from tool defaults (not project YAML)
        let proto_model = crate::util::get_default_prototype_model();
        let explain_model = crate::util::get_default_explain_model();
        println!("Prototype_model: {}", proto_model);
        println!("Explain_model: {}", explain_model);

        let has_openai = get_openai_api_key_from_env_or_config().is_some();
        if has_openai {
            println!("{} OpenAI API key detected. Note: prototyping uses OpenAI today; we're migrating to Ollama/open-source models soon.", sym_check(ce));
        } else {
            println!("{} Warning: No OpenAI API key detected. Prototyping features won't be available until a key is set.", sym_question(ce));
            println!("   You can set one with: qernel auth --set-openai-key");
        }
        return Ok(());
    }

    let mut changed = false;

    if let Some(p) = cmd.set.as_deref() {
        let v = p.trim().to_lowercase();
        if v != "openai" && v != "ollama" {
            anyhow::bail!("invalid provider '{}': expected 'openai' or 'ollama'", p);
        }
        cfg.provider = Some(v);
        changed = true;
    }

    if let Some(url) = cmd.base_url.as_deref() {
        let u = url.trim();
        if u.is_empty() { anyhow::bail!("base_url cannot be empty"); }
        cfg.ollama_base_url = Some(u.to_string());
        changed = true;
    }

    if changed { save_config(&cfg)?; }
    Ok(())
}


