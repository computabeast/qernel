use std::path::Path;
use std::process::Command;

use anyhow::{Context, Result};
use indicatif::{ProgressBar, ProgressStyle};

fn is_full_url(s: &str) -> bool {
    s.starts_with("http://") || s.starts_with("https://") || s.starts_with("git@")
}

fn join_base_repo(base: &str, repo: &str) -> String {
    let mut b = base.to_string();
    if !b.ends_with('/') { b.push('/'); }
    let r = repo.trim_start_matches('/');
    format!("{}{}", b, r)
}

pub fn handle_pull(repo: String, dest: String, branch: Option<String>, server: String) -> Result<()> {
    let ce = crate::util::color_enabled_stdout();
    let dest_path = Path::new(&dest);
    if dest_path.exists() {
        anyhow::bail!("destination already exists: {}", dest_path.display());
    }

    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} cloning repo...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));

    // Determine clone URL
    let url = if is_full_url(&repo) {
        repo
    } else {
        join_base_repo(&server, &repo)
    };

    let mut cmd = Command::new("git");
    cmd.arg("clone");
    if let Some(br) = branch.as_ref() { cmd.args(["--branch", br]); }
    cmd.args([&url, &dest]);

    let status = cmd.status().context("git clone failed")?;
    pb.finish_and_clear();

    if status.success() {
        println!("{} Cloned {} -> {}", crate::util::sym_check(ce), url, dest);
    } else {
        println!("{} Clone failed", crate::util::sym_cross(ce));
    }

    Ok(())
}
