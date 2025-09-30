use anyhow::{bail, Context, Result};
use indicatif::{ProgressBar, ProgressStyle};
use std::env;
use std::io::{self, Read};

use crate::util::{load_config, save_config};

pub fn handle_login() -> Result<()> {
    let ce = crate::util::color_enabled_stdout();
    println!("{} Enter your personal access token (or set QERNEL_TOKEN):", crate::util::sym_question(ce));
    let token = match rpassword::read_password() {
        Ok(t) => t,
        Err(_) => {
            if let Ok(t) = env::var("QERNEL_TOKEN") { t } else {
                let mut buf = String::new();
                io::stdin().read_to_string(&mut buf).context("failed to read token from stdin")?;
                buf
            }
        }
    };
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
    let ce = crate::util::color_enabled_stdout();
    println!("{} Logged in successfully.", crate::util::sym_check(ce));
    Ok(())
}
