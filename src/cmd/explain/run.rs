use anyhow::{Context, Result};
use std::path::PathBuf;

use super::chunk::{ChunkGranularity, PythonChunk, chunk_python_or_fallback};
use super::prompts::build_snippet_prompt;
use super::network::call_text_model;
use crate::util::get_openai_api_key_from_env_or_config;
use super::renderer::{render_console, render_markdown_report, RenderOptions};
use serde::Deserialize;
use indicatif::{ProgressBar, ProgressStyle};

#[derive(Deserialize)]
struct SnippetSummary { id: String, summary: String }

pub fn handle_explain(
    files: Vec<String>,
    per: String,
    model: String,
    markdown: bool,
    output: Option<String>,
    pager: bool,
    max_chars: Option<usize>,
) -> Result<()> {
    if files.is_empty() {
        anyhow::bail!("no files provided");
    }

    let granularity = match per.as_str() {
        "function" => ChunkGranularity::Function,
        "class" => ChunkGranularity::Class,
        "block" => ChunkGranularity::Block,
        other => anyhow::bail!("unsupported --per value: {}", other),
    };

    // Output dir for markdown
    let output_dir = if markdown {
        if let Some(o) = output.as_ref() {
            Some(PathBuf::from(o))
        } else {
            Some(PathBuf::from(".qernel/explain"))
        }
    } else { None };

    if let Some(dir) = output_dir.as_ref() { std::fs::create_dir_all(dir).ok(); }

    // For now, sequential per file; we can parallelize later with a concurrency cap.
    for file in files {
        let path = PathBuf::from(&file);
        let content = std::fs::read_to_string(&path).with_context(|| format!("read file {}", file))?;

        // Large-file rule: warn if >1000 lines
        let total_lines = content.lines().count();
        let large_file = total_lines > 1000;
        if large_file {
            eprintln!("[WARNING] File {} exceeds 1000 lines; using truncated full-file context plus local window per snippet.", file);
        }

        let snippets: Vec<PythonChunk> = chunk_python_or_fallback(&content, &path, granularity)?;

        // Concurrent per-snippet calls (bounded)
        let api_key = get_openai_api_key_from_env_or_config().unwrap_or_default();
        let max_workers = std::env::var("QERNEL_EXPLAIN_WORKERS").ok().and_then(|s| s.parse::<usize>().ok()).unwrap_or(4);

        let mut handles: Vec<std::thread::JoinHandle<(usize, String)>> = Vec::new();
        let mut results: Vec<Option<String>> = vec![None; snippets.len()];

        // Progress bar for snippet processing
        let pb = ProgressBar::new(snippets.len() as u64);
        pb.set_style(ProgressStyle::with_template("{spinner:.green} [{elapsed_precise}<{eta_precise}] {bar:40.cyan/blue} {pos}/{len} snippets")
            .unwrap()
            .progress_chars("=>-"));
        // Keep spinner animating even when waiting on network calls
        pb.enable_steady_tick(std::time::Duration::from_millis(120));

        for (idx, snip) in snippets.iter().cloned().enumerate() {
            let (system, user) = build_snippet_prompt(&file, &content, &snip, max_chars, large_file);

            if handles.len() >= max_workers {
                if let Some(h) = handles.pop() {
                    let (i_done, txt) = h.join().unwrap_or((idx, String::from("(error: join failed)")));
                    results[i_done] = Some(txt);
                    pb.inc(1);
                }
            }

            let model_cl = model.clone();
            let api_key_cl = api_key.clone();
            let handle = std::thread::spawn(move || {
                let text = if api_key_cl.is_empty() {
                    super::prompts::mock_call_model(&model_cl, &system, &user).unwrap_or_else(|_| "(mock explanation)".to_string())
                } else {
                    call_text_model(&api_key_cl, &model_cl, &system, &user).unwrap_or_else(|e| format!("(error: {})", e))
                };
                (idx, text)
            });
            handles.insert(0, handle);
        }

        for h in handles {
            let (i_done, txt) = h.join().unwrap_or((0, String::from("(error: join failed)")));
            results[i_done] = Some(txt);
            pb.inc(1);
        }
        pb.finish_and_clear();

        // Assemble outputs in original order
        let mut rendered_blocks: Vec<String> = Vec::with_capacity(snippets.len());
        for (i, snip) in snippets.iter().enumerate() {
            let explanation = results[i].clone().unwrap_or_else(|| "(no explanation)".to_string());
            // Parse structured JSON; fallback to raw text
            let parsed: Option<SnippetSummary> = serde_json::from_str(&explanation).ok();
            // Touch id so the field isn't considered dead code
            let _parsed_id_used = parsed.as_ref().map(|p| p.id.as_str()).unwrap_or("");
            let summary = parsed.as_ref().map(|p| p.summary.as_str()).unwrap_or(explanation.trim());
            let console_block = render_console(&file, snip, summary)?;
            rendered_blocks.push(console_block);
            if let Some(dir) = output_dir.as_ref() {
                render_markdown_report(dir, &file, snip, summary)?;
            }
        }

        let options = RenderOptions { pager };
        super::renderer::print_blocks(rendered_blocks.join("\n"), &options)?;
    }

    Ok(())
}


