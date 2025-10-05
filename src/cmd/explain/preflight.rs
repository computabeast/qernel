use anyhow::Result;
use std::path::PathBuf;

use crate::config::load_config as load_proj_config;

pub fn check_explain(files: Vec<String>, _model: Option<String>) -> Result<()> {
    if files.is_empty() { anyhow::bail!("no files provided"); }
    // Ensure files exist
    for f in &files {
        let p = std::path::Path::new(f);
        if !p.exists() { anyhow::bail!("file not found: {}", f); }
    }

    // Resolve model from project config vs CLI
    let cwd = std::env::current_dir().unwrap_or(PathBuf::from("."));
    let proj_cfg_path = cwd.join(".qernel").join("qernel.yaml");
    let configured_model = if proj_cfg_path.exists() {
        let default_model = crate::util::get_default_explain_model();
        let yaml_model = load_proj_config(&proj_cfg_path)
            .ok()
            .and_then(|c| c.explain_model);
        if let Some(y) = yaml_model.as_ref() {
            if y != &default_model {
                println!(
                    "Warning: YAML explain_model '{}' differs from tool default '{}'. YAML takes precedence at runtime.",
                    y, default_model
                );
            }
        }
        yaml_model.unwrap_or(default_model)
    } else {
        crate::util::get_default_explain_model()
    };
    // For --check, always use configured precedence (YAML -> tool default),
    // ignoring the CLI default model value to avoid accidental overrides.
    let effective_model = configured_model;

    // Provider preflight
    let client = crate::common::network::default_client(10)?;
    let provider = crate::common::network::detect_provider();
    crate::common::network::preflight_check(&client, provider, &effective_model)?;
    println!("Explain preflight passed for model '{}'.", effective_model);
    Ok(())
}


