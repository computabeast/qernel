use std::process::Command;

use anyhow::{Context, Result};
use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};

pub fn handle_push(remote: String, url: Option<String>, branch: Option<String>) -> Result<()> {
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} pushing...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));

    if let Some(url) = url.as_ref() {
        // Set or update remote
        let _ = Command::new("git").args(["remote", "remove", &remote]).output();
        Command::new("git")
            .args(["remote", "add", &remote, url])
            .output()
            .context("failed to set remote")?;
    }

    // Determine branch
    let current_branch = if let Some(b) = branch {
        b
    } else {
        let out = Command::new("git")
            .args(["rev-parse", "--abbrev-ref", "HEAD"])
            .output()
            .context("failed to determine current branch")?;
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    };

    // Push
    let status = Command::new("git")
        .args(["push", &remote, &format!("HEAD:{}", current_branch)])
        .status()
        .context("git push failed")?;

    pb.finish_and_clear();
    if status.success() {
        println!("{} Pushed to {} {}", "✔".green().bold(), remote, current_branch);
    } else {
        println!("{} Push failed", "✖".red().bold());
    }

    Ok(())
}
