use anyhow::{Context, Result};
use std::path::PathBuf;
use std::io::IsTerminal;

use super::chunk::PythonChunk;
use crate::cmd::prototype::console::ConsoleStreamer;
use syntect::parsing::SyntaxSet;
use syntect::highlighting::ThemeSet;
use syntect::easy::HighlightLines;
use syntect::util::as_24_bit_terminal_escaped;
use once_cell::sync::Lazy;

pub struct RenderOptions { pub pager: bool }

static PS: Lazy<SyntaxSet> = Lazy::new(|| SyntaxSet::load_defaults_newlines());
static TS: Lazy<ThemeSet> = Lazy::new(|| ThemeSet::load_defaults());

pub fn render_console(_file: &str, snip: &PythonChunk, explanation: &str) -> Result<String> {
    let mut out = String::new();
    // Gray padded header with subtle background
    const RESET: &str = "\x1b[0m";
    const GRAY: &str = "\x1b[90m";
    const BG_SOFT: &str = "\x1b[48;5;240m";
    let header = format!("[{} -> {}]  {} {}  (id={})", snip.start_line, snip.end_line, snip.kind, snip.name, snip.id);
    out.push_str(BG_SOFT);
    out.push_str(GRAY);
    out.push(' ');
    out.push_str(&header);
    out.push(' ');
    out.push_str(RESET);
    out.push('\n');
    out.push('\n');
    // Summary in default terminal color (explicit reset, no ANSI styling)
    out.push_str(RESET);
    out.push_str(explanation.trim());
    out.push_str(RESET);
    out.push('\n');
    out.push('\n');
    // Syntax highlighted code with line numbers
    // Force Python syntax highlighting per docs
    let syntax = PS.find_syntax_by_token("Python").or_else(|| PS.find_syntax_by_extension("py")).unwrap_or(PS.find_syntax_plain_text());
    let theme = TS.themes.get("InspiredGitHub").or_else(|| TS.themes.get("base16-ocean.dark")).unwrap_or_else(|| TS.themes.values().next().expect("theme"));
    let mut h = HighlightLines::new(syntax, theme);
    for (i, line) in snip.code.lines().enumerate() {
        let n = snip.start_line + i;
        let ranges = h.highlight_line(line, &PS).unwrap_or_default();
        let escaped = as_24_bit_terminal_escaped(&ranges[..], false);
        out.push_str(&format!("{:>6} | {}\n", n, escaped));
    }
    // Reset color after code block and add spacing
    out.push_str("\x1b[0m\n\n");
    Ok(out)
}

pub fn print_blocks(assembled: String, opts: &RenderOptions) -> Result<()> {
    if opts.pager && std::io::stdout().is_terminal() {
        // Attempt to page with less -R
        let mut child = std::process::Command::new("less")
            .arg("-R")
            .stdin(std::process::Stdio::piped())
            .spawn()
            .context("spawn less")?;
        use std::io::Write;
        if let Some(mut stdin) = child.stdin.take() {
            stdin.write_all(assembled.as_bytes()).ok();
        }
        let _ = child.wait();
        return Ok(());
    }
    let console = ConsoleStreamer::new();
    console.println(&assembled)?;
    Ok(())
}

pub fn render_markdown_report(dir: &PathBuf, file: &str, snip: &PythonChunk, explanation: &str) -> Result<()> {
    let base = std::path::Path::new(file).file_stem().and_then(|s| s.to_str()).unwrap_or("report");
    let md_path = dir.join(format!("{}{}.md", base, ""));
    let mut md = String::new();
    md.push_str(&format!("\n### {}:{}-{} {} {}\n\n", file, snip.start_line, snip.end_line, snip.kind, snip.name));
    md.push_str(&format!("_id: {}_\n\n", snip.id));
    md.push_str(explanation.trim());
    md.push_str("\n\n");
    md.push_str("```python\n");
    md.push_str(&format!("# lines {}-{}\n", snip.start_line, snip.end_line));
    md.push_str(&snip.code);
    md.push_str("\n```\n");

    // Append per file
    use std::fs::{OpenOptions};
    let mut f = OpenOptions::new().create(true).append(true).open(&md_path).with_context(|| format!("open {}", md_path.display()))?;
    use std::io::Write;
    f.write_all(md.as_bytes())?;
    Ok(())
}


