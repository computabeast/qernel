use std::fs;
use std::path::Path;
use std::process::Command;

use anyhow::{Context, Result};
use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};

pub fn handle_new(path: String, template: bool) -> Result<()> {
    let project_path = Path::new(&path);
    if project_path.exists() {
        anyhow::bail!("path already exists: {}", project_path.display());
    }

    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} scaffolding project...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));

    fs::create_dir_all(&project_path).with_context(|| "failed to create project dir")?;

    // Create basic structure
    let src_dir = project_path.join("src");
    let scripts_dir = project_path.join("scripts");
    let qk_dir = project_path.join("qernel");
    fs::create_dir_all(&src_dir)?;
    fs::create_dir_all(&scripts_dir)?;
    fs::create_dir_all(&qk_dir)?;

    // Write a README and .gitignore
    fs::write(project_path.join("README.md"), "# New Qernel Project\n")?;
    fs::write(project_path.join(".gitignore"), ".DS_Store\n/target\n/node_modules\n.env\n")?;

    // Optional template placeholders
    if template {
        fs::write(src_dir.join("main.qk"), "// entrypoint for quantum kernel\n")?;
        fs::write(qk_dir.join("config.toml"), "[project]\nname=\"qernel_app\"\n")?;
    }

    // Initialize git repository
    Command::new("git").arg("init").current_dir(&project_path).output().context("git init failed")?;
    Command::new("git").args(["add", "."]).current_dir(&project_path).output().ok();
    Command::new("git").args(["commit", "-m", "chore: initial scaffold"]).current_dir(&project_path).output().ok();

    pb.finish_with_message("done");
    println!("{} Created project at {}", "✔".green().bold(), project_path.display());

    Ok(())
}
