use anyhow::Result;
use clap::Args;
use crate::util::{load_config, save_config, Config};

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

    /// Interactive picker to choose provider and default models
    #[arg(long)]
    pub pick: bool,
}

pub fn handle_provider(cmd: ProviderCmd) -> Result<()> {
    let mut cfg: Config = load_config().unwrap_or_default();
    if cmd.list {
        println!("qernel");
        println!("ollama");
        return Ok(());
    }
    if cmd.check {
        use reqwest::blocking::Client;
        use crate::common::network::{default_client, detect_provider, preflight_check};
        let model = cmd.model.as_deref().unwrap_or("qernel-auto");
        let client: Client = default_client(15)?;
        let provider = detect_provider();
        preflight_check(&client, provider, model)?;
        println!("Preflight passed for provider and model '{}'.", model);
        return Ok(());
    }
    if cmd.pick {
        use std::io::{self, Write};
        fn prompt(prompt: &str) -> String {
            print!("{}", prompt);
            io::stdout().flush().ok();
            let mut s = String::new();
            io::stdin().read_line(&mut s).ok();
            s.trim().to_string()
        }

        println!("Select provider:");
        println!("  1) qernel");
        println!("  2) ollama");
        let choice = prompt("Enter number [1]: ");
        let provider = match choice.as_str() {
            "2" => "ollama",
            _ => "qernel",
        };
        cfg.provider = Some(provider.to_string());

        let (default_proto, default_explain) = match provider {
            "qernel" => ("qernel-auto", "qernel-auto"),
            "ollama" => ("llama3.1:8b", "llama3.1:8b"),
            _ => ("qernel-auto", "qernel-auto"),
        };

        let proto = prompt(&format!("Prototype model [{}]: ", default_proto));
        let explain = prompt(&format!("Explain model    [{}]: ", default_explain));
        cfg.default_prototype_model = Some(if proto.is_empty() { default_proto.to_string() } else { proto });
        cfg.default_explain_model = Some(if explain.is_empty() { default_explain.to_string() } else { explain });

        if provider == "ollama" {
            let base = prompt(&format!("Ollama base URL [{}]: ", cfg.ollama_base_url.as_deref().unwrap_or("http://localhost:11434/v1")));
            if !base.trim().is_empty() { cfg.ollama_base_url = Some(base); }
        }

        save_config(&cfg)?;
        println!("Saved provider '{}' with prototype='{}' and explain='{}'.",
            provider,
            cfg.default_prototype_model.as_deref().unwrap_or(""),
            cfg.default_explain_model.as_deref().unwrap_or("")
        );
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
        println!("Provider: {}", cfg.provider.as_deref().unwrap_or("qernel"));
        println!("Ollama_base_url: {}", cfg.ollama_base_url.as_deref().unwrap_or("(unset, default http://localhost:11434/v1)"));

        // Show command-model mapping from tool defaults (not project YAML)
        let proto_model = crate::util::get_default_prototype_model();
        let explain_model = crate::util::get_default_explain_model();
        println!("Prototype_model: {}", proto_model);
        println!("Explain_model: {}", explain_model);
        return Ok(());
    }

    let mut changed = false;

    if let Some(p) = cmd.set.as_deref() {
        let v = p.trim().to_lowercase();
        if v != "ollama" && v != "qernel" {
            anyhow::bail!("invalid provider '{}': expected 'qernel' or 'ollama'", p);
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


