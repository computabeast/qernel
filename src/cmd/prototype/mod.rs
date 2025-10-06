pub mod agent;
pub mod console;
pub mod environment;
pub mod logging;
pub mod mineru;
pub mod network;
pub mod prompts;
pub mod snapshots;
pub mod validation;

use anyhow::{Context, Result};
use std::path::Path;
use std::io::{self, Write};

use crate::config::load_config;
use crate::cmd::prototype::logging::{debug_log, init_debug_logging};
use crate::config::save_config;

/// Main prototype handler - orchestrates the entire prototype workflow
pub fn handle_prototype(cwd: String, model: String, max_iters: u32, debug: bool, spec_only: bool, spec_and_content_only: bool) -> Result<()> {
    let cwd_path = Path::new(&cwd);
    let cwd_abs = cwd_path.canonicalize().unwrap_or_else(|_| cwd_path.to_path_buf());
    
    // Load configuration from .qernel
    let config_path = cwd_abs.join(".qernel").join("qernel.yaml");
    let mut config = load_config(&config_path)?;
    
    // Resolve effective model: prefer project config unless CLI explicitly overrides and user confirms
    if !model.is_empty() && model != config.agent.model {
        // Prefer YAML precedence; ask to override YAML with CLI configured default
        if ask_confirm(&format!(
            "Project YAML model is '{}'. Override with CLI model '{}'? [y/N]: ",
            config.agent.model, model
        ))? {
            config.agent.model = model;
        }
    }
    if max_iters > 0 && max_iters != 15 {
        // Only override if a different max_iters was explicitly provided
        config.agent.max_iterations = max_iters;
    }
    
    // Initialize debug logging
    let debug_file = init_debug_logging(&cwd_abs, debug)?;
    
    debug_log(&debug_file, "🔬 Starting prototype implementation...", debug);
    
    // Conditional ingestion based on flags
    if !spec_only && !spec_and_content_only {
        // Process any papers from config
        mineru::process_papers(&config.papers, &cwd_abs)?;
        
        // Process any content files from config
        if let Some(content_files) = &config.content_files {
            mineru::process_content_files(content_files, &cwd_abs)?;
        }
    } else if spec_and_content_only {
        // Skip papers, process content files only
        if let Some(content_files) = &config.content_files {
            mineru::process_content_files(content_files, &cwd_abs)?;
        }
    } // spec_only: skip both
    
    // Read .qernel/spec.md for implementation goals
    let goal = read_spec_goal(&cwd_abs)?;
    
    // Read benchmark command from config
    let test_cmd = config.benchmarks.test_command.clone();
    
    // Run agent loop
    debug_log(&debug_file, "🤖 Starting agent optimization...", debug);
    agent::run_agent_loop(
        cwd_abs.to_string_lossy().to_string(),
        goal,
        test_cmd,
        config.agent.model,
        config.agent.max_iterations,
        debug,
    )
}

pub fn check_prototype(cwd: String, model: String) -> Result<()> {
    let cwd_path = Path::new(&cwd);
    let cwd_abs = cwd_path.canonicalize().unwrap_or_else(|_| cwd_path.to_path_buf());
    let config_path = cwd_abs.join(".qernel").join("qernel.yaml");
    let config = load_config(&config_path)?;

    // Warn if YAML model differs from tool default
    let tool_default = crate::util::get_default_prototype_model();
    if config_path.exists() && config.agent.model != tool_default {
        println!(
            "Warning: YAML prototype model '{}' differs from tool default '{}'. YAML takes precedence at runtime.",
            config.agent.model, tool_default
        );
    }

    // Resolve model from config vs CLI
    let effective_model = if !model.is_empty() && model != config.agent.model { model } else { config.agent.model };

    // Preflight provider + model
    let client = crate::common::network::default_client(10)?;
    let provider = crate::common::network::detect_provider();
    crate::common::network::preflight_check(&client, provider, &effective_model)?;
    println!("Prototype preflight passed for model '{}'.", effective_model);
    Ok(())
}

/// Quickstart: scaffold a project for an arXiv URL then run prototype
pub fn quickstart_arxiv(url: String, model: String, max_iters: u32, debug: bool) -> Result<()> {
    // 1) Derive folder name from arXiv id
    let id = parse_arxiv_id(&url).unwrap_or_else(|| "paper".to_string());
    let folder = format!("arxiv-{}", id);

    // 2) Scaffold new project with template
    crate::cmd::new::handle_new(folder.clone(), true)?;

    // 3) Update .qernel/qernel.yaml with the arXiv URL
    let proj_path = std::path::Path::new(&folder);
    let config_path = proj_path.join(".qernel").join("qernel.yaml");
    let mut cfg = load_config(&config_path)?;
    cfg.papers = vec![crate::config::PaperConfig { url: url.clone() }];
    save_config(&cfg, &config_path)?;

    // 4) Run prototype in that folder
    handle_prototype(folder, model, max_iters, debug, false, false)
}

fn parse_arxiv_id(url: &str) -> Option<String> {
    // Handles /abs/<id>[vN], /pdf/<id>[vN].pdf, or raw ids
    let url = url.trim();
    if let Some(idx) = url.find("arxiv.org/") {
        let rest = &url[idx..];
        let parts: Vec<&str> = rest.split('/').collect();
        if let Some(pos) = parts.iter().position(|p| *p == "abs" || *p == "pdf") {
            if let Some(idpart) = parts.get(pos + 1) {
                let mut id = idpart.to_string();
                if let Some(dotpdf) = id.find(".pdf") { id.truncate(dotpdf); }
                return Some(id);
            }
        }
    }
    // Fallback: if looks like an id
    let clean = url.trim_end_matches(".pdf");
    if clean.chars().all(|c| c.is_ascii_alphanumeric() || c == '/' || c == '.' || c == 'v') {
        return Some(clean.to_string());
    }
    None
}

fn read_spec_goal(cwd: &Path) -> Result<String> {
    let spec_path = cwd.join(".qernel").join("spec.md");
    if !spec_path.exists() {
        anyhow::bail!(".qernel/spec.md not found. Please create a project with 'qernel new --template' first.");
    }

    let spec_content = std::fs::read_to_string(&spec_path)
        .context("Failed to read .qernel/spec.md")?;

    Ok(spec_content)
}

fn ask_confirm(prompt: &str) -> Result<bool> {
    print!("{}", prompt);
    io::stdout().flush().ok();
    let mut buf = String::new();
    io::stdin().read_line(&mut buf).ok();
    let ans = buf.trim().to_lowercase();
    Ok(ans == "y" || ans == "yes")
}
