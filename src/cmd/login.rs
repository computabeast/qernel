use anyhow::{bail, Context, Result};
use colored::Colorize;
use indicatif::{ProgressBar, ProgressStyle};

use crate::util::{load_config, save_config};

pub fn handle_login() -> Result<()> {
    println!("{} Enter your personal access token:", "?".cyan().bold());
    let token = rpassword::read_password().context("failed to read token")?;
    if token.trim().is_empty() {
        bail!("token cannot be empty");
    }

    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} saving token...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));

    let mut cfg = load_config().unwrap_or_default();
    cfg.token = Some(token.trim().to_string());
    save_config(&cfg)?;

    pb.finish_with_message("saved");
    println!("{} Logged in successfully.", "✔".green().bold());
    Ok(())
}
