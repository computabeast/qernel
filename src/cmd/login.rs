use anyhow::{bail, Context, Result};
use indicatif::{ProgressBar, ProgressStyle};
use std::env;
use std::io::{self, Read};

use crate::util::{load_config, save_config, get_openai_api_key_from_env_or_config, set_openai_api_key_in_config, unset_openai_api_key_in_config};
use owo_colors::OwoColorize;
use reqwest::blocking::Client;
use serde::Deserialize;

#[derive(Deserialize, Default)]
struct WhoAmIResponse {
    user_id: Option<String>,
    email: Option<String>,
    #[serde(rename = "screen_name")]
    screen_name: Option<String>,
}

pub fn handle_auth_with_flags(set_openai_key: bool, unset_openai_key: bool) -> Result<()> {
    let ce = crate::util::color_enabled_stdout();
    // Handle OpenAI key management flags first
    if set_openai_key {
        println!("Enter your OpenAI API key (or set OPENAI_API_KEY):");
        let key = match rpassword::read_password() {
            Ok(k) => if k.trim().is_empty() { std::env::var("OPENAI_API_KEY").unwrap_or_default() } else { k },
            Err(_) => std::env::var("OPENAI_API_KEY").unwrap_or_default(),
        };
        if key.trim().is_empty() {
            anyhow::bail!("OpenAI API key cannot be empty");
        }
        set_openai_api_key_in_config(&key)?;
        println!("{} OpenAI API key saved to local config.", crate::util::sym_check(ce));
        println!("Note: We're migrating to Ollama/open-source models soon.");
        return Ok(());
    }
    if unset_openai_key {
        unset_openai_api_key_in_config()?;
        println!("{} Removed stored OpenAI API key.", crate::util::sym_check(ce));
        return Ok(());
    }
    // If we already have a token, show masked and attempt to fetch identity
    if let Ok(cfg) = load_config() {
        if let Some(token) = cfg.token.as_ref() {
            let masked = if token.len() > 8 { format!("{}...", &token[..8]) } else { "...".to_string() };
            println!("{} Personal access token: {}", crate::util::sym_check(ce), masked.blue().bold());
            // Also surface OpenAI key status
            let has_openai = get_openai_api_key_from_env_or_config().is_some();
            if has_openai {
                println!("{} OpenAI API key detected. Note: prototyping uses OpenAI today; we're migrating to Ollama/open-source models soon.", crate::util::sym_check(ce));
            } else {
                println!("{} Warning: No OpenAI API key detected. Prototyping features won't be available until a key is set.", crate::util::sym_question(ce));
                println!("   You can set one with: qernel auth --set-openai-key");
            }

            if let Ok(client) = Client::builder().timeout(std::time::Duration::from_secs(10)).build() {
                if let Ok(r) = client
                    .get("https://dojoservice.onrender.com/_api/whoami")
                    .bearer_auth(token)
                    .send() {
                    if r.status().is_success() {
                        if let Ok(info) = r.json::<WhoAmIResponse>() {
                            if let Some(email) = info.email { println!("{} Email: {}", crate::util::sym_check(ce), email); }
                            if let Some(name) = info.screen_name { println!("{} Name: {}", crate::util::sym_check(ce), name); }
                            if let Some(uid) = info.user_id { println!("{} User ID: {}", crate::util::sym_check(ce), uid); }
                        }
                        return Ok(());
                    } else {
                        println!("Token appears invalid or expired. Please enter a new PAT.");
                    }
                }
            }
        }
    }

    println!("Enter your personal access token (or set QERNEL_TOKEN):");
    let token = match rpassword::read_password() {
        Ok(t) => t,
        Err(_) => {
            if let Ok(t) = env::var("QERNEL_TOKEN") { t } else {
                let mut buf = String::new();
                io::stdin().read_to_string(&mut buf).context("Failed to read token from stdin")?;
                buf
            }
        }
    };
    if token.trim().is_empty() {
        bail!("Token cannot be empty");
    }

    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} Saving token...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));

    let mut cfg = load_config().unwrap_or_default();
    cfg.token = Some(token.trim().to_string());
    save_config(&cfg)?;

    pb.finish_with_message("Token Saved");
    let ce = crate::util::color_enabled_stdout();
    println!("{} Personal access token saved.", crate::util::sym_check(ce));

    if let Ok(client) = Client::builder().timeout(std::time::Duration::from_secs(10)).build() {
        if let Ok(r) = client
            .get("https://dojoservice.onrender.com/_api/whoami")
            .bearer_auth(token.trim())
            .send() {
            if r.status().is_success() {
                if let Ok(info) = r.json::<WhoAmIResponse>() {
                    let masked = if token.len() > 8 { format!("{}...", &token[..8]) } else { "...".to_string() };
                    println!("{} Personal access token: {}", crate::util::sym_check(ce), masked.blue().bold());
                    if let Some(email) = info.email { println!("{} Email: {}", crate::util::sym_check(ce), email); }
                    if let Some(name) = info.screen_name { println!("{} Name: {}", crate::util::sym_check(ce), name); }
                    if let Some(uid) = info.user_id { println!("{} User ID: {}", crate::util::sym_check(ce), uid); }
                }
            } else {
                println!("If you don’t have a token, get one at {}", "https://www.qernelzoo.com/profile".underline());
            }
        }
    }
    Ok(())
}
