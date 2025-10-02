use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

use anyhow::{Context, Result};
use indicatif::{ProgressBar, ProgressStyle};
use crate::util::load_config;

pub fn handle_push(remote: String, url: Option<String>, branch: Option<String>, no_commit: bool) -> Result<()> {
    let ce = crate::util::color_enabled_stdout();
    
    // Step 1: Set up remote if URL provided
    if let Some(url) = url.as_ref() {
        println!("{} Setting up remote '{}'...", crate::util::sym_gear(ce), remote);
        
        // Load stored token for authentication
        let config = load_config().unwrap_or_default();
        let authenticated_url = if let Some(token) = config.token {
            // Replace https:// with https://x:token@ for authentication
            if url.starts_with("https://") {
                format!("https://x:{}@{}", token, &url[8..])
            } else {
                url.clone()
            }
        } else {
            println!("{} Warning: No stored token found. You may need to run 'qernel auth' first.", crate::util::sym_question(ce));
            url.clone()
        };
        
        // Remove existing remote (ignore errors)
        let _ = Command::new("git")
            .args(["remote", "remove", &remote])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .output();
        
        // Add new remote with authentication
        let remote_output = Command::new("git")
            .args(["remote", "add", &remote, &authenticated_url])
            .output()
            .context("failed to set remote")?;
        
        if !remote_output.status.success() {
            let error = String::from_utf8_lossy(&remote_output.stderr);
            anyhow::bail!("Failed to add remote: {}", error);
        }
        
        println!("{} Remote '{}' configured with authentication", crate::util::sym_check(ce), remote);
    }

    // Step 2: Determine branch
    let current_branch = if let Some(b) = branch {
        b
    } else {
        println!("{} Detecting current branch...", crate::util::sym_gear(ce));
        let out = Command::new("git")
            .args(["rev-parse", "--abbrev-ref", "HEAD"])
            .output()
            .context("failed to determine current branch")?;
        
        if !out.status.success() {
            let error = String::from_utf8_lossy(&out.stderr);
            anyhow::bail!("Failed to get current branch: {}", error);
        }
        
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    };
    
    println!("{} Branch: {}", crate::util::sym_check(ce), current_branch);

    // Step 3: Auto-commit changes if any exist (unless --no-commit flag is used)
    if !no_commit {
        let status_output = Command::new("git")
            .args(["status", "--porcelain"])
            .output()
            .context("failed to check git status")?;
        
        if status_output.status.success() {
            let status = String::from_utf8_lossy(&status_output.stdout);
            if !status.trim().is_empty() {
                println!("{} Staging changes...", crate::util::sym_gear(ce));
                
                // Stage all changes
                let add_output = Command::new("git")
                    .args(["add", "."])
                    .output()
                    .context("failed to stage changes")?;
                
                if !add_output.status.success() {
                    let error = String::from_utf8_lossy(&add_output.stderr);
                    anyhow::bail!("Failed to stage changes: {}", error);
                }
                
                // Commit changes
                println!("{} Committing changes...", crate::util::sym_gear(ce));
                let commit_output = Command::new("git")
                    .args(["commit", "-m", "Auto-commit before push"])
                    .output()
                    .context("failed to commit changes")?;
                
                if !commit_output.status.success() {
                    let error = String::from_utf8_lossy(&commit_output.stderr);
                    anyhow::bail!("Failed to commit changes: {}", error);
                }
                
                println!("{} Changes committed", crate::util::sym_check(ce));
            } else {
                println!("{} No changes to commit", crate::util::sym_check(ce));
            }
        }
    } else {
        println!("{} Skipping auto-commit (--no-commit flag)", crate::util::sym_gear(ce));
    }

    // Step 4: Push with progress and timeout handling
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} Pushing...").unwrap());
    pb.enable_steady_tick(Duration::from_millis(100));
    
    // Use git push with verbose output and timeout
    let start_time = Instant::now();
    let timeout_duration = Duration::from_secs(300); // 5 minutes
    
    // Clone values before moving into closure
    let remote_clone = remote.clone();
    let current_branch_clone = current_branch.clone();
    
    let push_result = std::thread::spawn(move || {
        Command::new("git")
            .args(["push", "--verbose", &remote_clone, &format!("HEAD:{}", current_branch_clone)])
            .output()
    });
    
    // Wait for push with timeout using a simple polling approach
    let push_output = loop {
        if start_time.elapsed() > timeout_duration {
            anyhow::bail!("Push timed out after 5 minutes");
        }
        
        if push_result.is_finished() {
            break match push_result.join() {
                Ok(output) => output,
                Err(e) => anyhow::bail!("Push thread error: {:?}", e),
            };
        }
        
        // Small sleep to avoid busy waiting
        std::thread::sleep(Duration::from_millis(100));
    };
    
    pb.finish_and_clear();

    // Handle the Result<Output, std::io::Error>
    match push_output {
        Ok(output) => {
            if output.status.success() {
                println!("{} Successfully pushed to {} {}", crate::util::sym_check(ce), remote, current_branch);
                
                // Show any additional output from git
                let stdout = String::from_utf8_lossy(&output.stdout);
                if !stdout.trim().is_empty() {
                    println!("{}", stdout);
                }
            } else {
                let stderr = String::from_utf8_lossy(&output.stderr);
                let stdout = String::from_utf8_lossy(&output.stdout);
                
                println!("{} Push failed to {} {}", crate::util::sym_cross(ce), remote, current_branch);
                
                if !stderr.trim().is_empty() {
                    println!("Error: {}", stderr);
                }
                if !stdout.trim().is_empty() {
                    println!("Output: {}", stdout);
                }
                
                anyhow::bail!("Git push failed");
            }
        }
        Err(e) => {
            let error_msg = e.to_string();
            if error_msg.contains("could not read Username") || error_msg.contains("Authentication failed") {
                println!("{} Push failed: Authentication required", crate::util::sym_cross(ce));
                println!("💡 Try running 'qernel auth' to store your token, then try again.");
            } else {
                println!("{} Push failed to {} {}: {}", crate::util::sym_cross(ce), remote, current_branch, e);
            }
            anyhow::bail!("Git push failed: {}", e);
        }
    }

    Ok(())
}
