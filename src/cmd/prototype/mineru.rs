use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use std::fs;

use crate::config::PaperConfig;

/// Process all papers from configuration
pub fn process_papers(papers: &[PaperConfig], cwd: &Path) -> Result<()> {
    for paper in papers {
        // Check if it's a local file (not a URL)
        if !paper.url.starts_with("http") && !paper.url.starts_with("arxiv") {
            let pdf_abs_path = cwd.join(&paper.url);
            if pdf_abs_path.exists() {
                println!("📄 Processing local PDF: {}", pdf_abs_path.display());
                process_local_pdf(&pdf_abs_path, cwd)?;
            } else {
                println!("⚠️  Local PDF not found: {}", pdf_abs_path.display());
            }
        } else {
            println!("📄 Processing remote paper: {}", paper.url);
            process_remote_paper(&paper.url, cwd)?;
        }
    }
    Ok(())
}

/// Process content files specified in the config
pub fn process_content_files(content_files: &[String], cwd: &Path) -> Result<()> {
    for content_file in content_files {
        let content_path = cwd.join(content_file);
        if content_path.exists() {
            println!("Processing content file: {}", content_path.display());
            update_spec_with_paper(&content_path, cwd)?;
        } else {
            println!("Content file not found: {}", content_path.display());
        }
    }
    Ok(())
}

fn process_remote_paper(url: &str, cwd: &Path) -> Result<()> {
    use indicatif::{ProgressBar, ProgressStyle};
    
    // Create directories
    let papers_dir = cwd.join(".qernel").join("papers");
    let parsed_dir = cwd.join(".qernel").join("parsed");
    fs::create_dir_all(&papers_dir)?;
    fs::create_dir_all(&parsed_dir)?;
    
    // Download the paper first
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} Downloading remote paper...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));
    
    let downloaded_pdf = download_paper(url, &papers_dir)?;
    pb.finish_with_message("Paper downloaded");
    
    // Now process the downloaded PDF
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} Processing downloaded paper with mineru...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));
    
    // Use the project's virtual environment mineru script directly
    let mineru_path = if cfg!(windows) {
        cwd.join(".qernel").join(".venv").join("Scripts").join("mineru.exe")
    } else {
        cwd.join(".qernel").join(".venv").join("bin").join("mineru")
    };
    
    let output = std::process::Command::new(&mineru_path)
        .args([
            "-p", downloaded_pdf.to_str().unwrap(),
            "-l", "en",
            "-b", "pipeline", 
            "-f", "true",
            "-t", "true",
            "-o", parsed_dir.to_str().unwrap(),
        ])
        .output()
        .context("Failed to run mineru. Make sure it's installed in the project venv with: pip install mineru[core]")?;
    
    // Show mineru output to user
    if !output.stdout.is_empty() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        println!("{}", stdout);
    }
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        if !stderr.is_empty() {
            println!("{}", stderr);
        }
        anyhow::bail!("mineru failed: {}", stderr);
    }
    
    pb.finish_with_message("Remote paper processed");
    println!("Remote paper processed with mineru");
    
    // Find and process the content JSON
    let content_json = find_content_json(&parsed_dir)?;
    update_spec_with_paper(&content_json, cwd)?;
    
    Ok(())
}

fn download_paper(url: &str, papers_dir: &Path) -> Result<PathBuf> {
    use reqwest::blocking::Client;
    
    // Create a filename from the URL
    let filename = if url.contains("arxiv.org") {
        // Extract arxiv ID for filename
        if let Some(id) = url.split('/').last() {
            format!("arxiv_{}.pdf", id.replace(".pdf", ""))
        } else {
            "downloaded_paper.pdf".to_string()
        }
    } else {
        // Generic filename for other URLs
        "downloaded_paper.pdf".to_string()
    };
    
    let pdf_path = papers_dir.join(&filename);
    
    // Download the PDF
    let client = Client::new();
    let response = client.get(url).send()
        .context("Failed to download paper")?;
    
    if !response.status().is_success() {
        anyhow::bail!("Failed to download paper: HTTP {}", response.status());
    }
    
    let mut file = std::fs::File::create(&pdf_path)
        .context("Failed to create PDF file")?;
    
    let mut content = std::io::Cursor::new(response.bytes()?);
    std::io::copy(&mut content, &mut file)
        .context("Failed to write PDF content")?;
    
    Ok(pdf_path)
}

fn process_local_pdf(pdf_path: &Path, cwd: &Path) -> Result<()> {
    use indicatif::{ProgressBar, ProgressStyle};
    
    // Create parsed directory inside .qernel
    let parsed_dir = cwd.join(".qernel").join("parsed");
    fs::create_dir_all(&parsed_dir)?;
    
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::with_template("{spinner} Processing PDF with mineru...").unwrap());
    pb.enable_steady_tick(std::time::Duration::from_millis(80));
    
    // Use the project's virtual environment mineru script directly
    let mineru_path = if cfg!(windows) {
        cwd.join(".qernel").join(".venv").join("Scripts").join("mineru.exe")
    } else {
        cwd.join(".qernel").join(".venv").join("bin").join("mineru")
    };
    
    let output = std::process::Command::new(&mineru_path)
        .args([
            "-p", pdf_path.to_str().unwrap(),
            "-l", "en",
            "-b", "pipeline", 
            "-f", "true",
            "-t", "true",
            "-o", parsed_dir.to_str().unwrap(),
        ])
        .output()
        .context("Failed to run mineru. Make sure it's installed in the project venv with: pip install mineru[core]")?;
    
    // Show mineru output to user
    if !output.stdout.is_empty() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        println!("{}", stdout);
    }
    
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        if !stderr.is_empty() {
            println!("{}", stderr);
        }
        anyhow::bail!("mineru failed: {}", stderr);
    }
    
    pb.finish_with_message("PDF processed");
    println!("PDF processed with mineru");
    
    // Find and process the content JSON
    let content_json = find_content_json(&parsed_dir)?;
    update_spec_with_paper(&content_json, cwd)?;
    
    Ok(())
}

fn find_content_json(parsed_dir: &Path) -> Result<PathBuf> {
    // Look for content_list.json files recursively
    let mut content_files = Vec::new();
    
    fn find_json_files(dir: &Path, files: &mut Vec<PathBuf>) -> Result<()> {
        if dir.is_dir() {
            for entry in fs::read_dir(dir)? {
                let entry = entry?;
                let path = entry.path();
                
                if path.is_dir() {
                    find_json_files(&path, files)?;
                } else if path.file_name()
                    .and_then(|n| n.to_str())
                    .map(|n| n.contains("content_list.json"))
                    .unwrap_or(false) {
                    files.push(path);
                }
            }
        }
        Ok(())
    }
    
    find_json_files(parsed_dir, &mut content_files)?;
    
    if content_files.is_empty() {
        anyhow::bail!("No content_list.json found in parsed directory");
    }
    
    // Use the most recent one
    use std::time::SystemTime;
    content_files.sort_by_key(|p| {
        fs::metadata(p).and_then(|m| m.modified()).unwrap_or(SystemTime::UNIX_EPOCH)
    });
    Ok(content_files.last().cloned().unwrap())
}

fn update_spec_with_paper(content_json_path: &Path, cwd: &Path) -> Result<()> {
    // Read the content JSON
    let content = fs::read_to_string(content_json_path)
        .context("Failed to read content JSON")?;
    
    let content_data: serde_json::Value = serde_json::from_str(&content)
        .context("Failed to parse content JSON")?;
    
    // Convert the entire JSON content to string
    let paper_text = serde_json::to_string_pretty(&content_data)
        .context("Failed to serialize content JSON")?;
    
    // Note: Images are now handled directly in the agent request, not in spec.md
    
    // Read existing .qernel/spec.md
    let spec_path = cwd.join(".qernel").join("spec.md");
    let mut spec_content = if spec_path.exists() {
        fs::read_to_string(&spec_path)?
    } else {
        String::new()
    };
    
    // Add/replace the Paper Content section idempotently
    let heading = "## Paper Content";
    let new_section = format!("{heading}\n\n{}\n", paper_text);
    if let Some(start) = spec_content.find(heading) {
         let after = start + heading.len();
         let end = spec_content[after..]
             .find("\n## ")
             .map(|i| after + i)
             .unwrap_or(spec_content.len());
         spec_content.replace_range(start..end, &new_section);
    } else {
         if !spec_content.ends_with('\n') { spec_content.push('\n'); }
         spec_content.push('\n');
         spec_content.push_str(&new_section);
    }
    
    // Images are now handled directly in the agent request, not added to spec.md
    
    fs::write(&spec_path, spec_content)?;
    
    println!("Updated .qernel/spec.md with paper content");
    
    Ok(())
}

