use anyhow::Result;

use super::chunk::PythonChunk;

pub fn build_snippet_prompt(
    filename: &str,
    full_content: &str,
    snip: &PythonChunk,
    max_chars: Option<usize>,
    large_file: bool,
) -> (String, String) {
    let limit = if let Some(m) = max_chars { format!(" Limit your summary to at most {} characters.", m) } else { String::new() };
    let system = format!(
        "You are a precise code explainer. Explain ONLY the requested snippet. Consider Python semantics and the snippet's position within the entire file. Do not propose changes or add code. Output MUST be strict JSON with exactly these keys: id, summary. No markdown, no code, no extra keys.{}",
        limit
    );

    // Truncate full file for very large files; always include exact snippet.
    let user = if large_file {
        let lines: Vec<&str> = full_content.lines().collect();
        let total = lines.len();
        let head = 400.min(total);
        let tail = 400.min(total.saturating_sub(head));
        let mut truncated = String::new();
        truncated.push_str(&lines[..head].join("\n"));
        truncated.push_str("\n...\n[TRUNCATED]\n...\n");
        if tail > 0 { truncated.push_str(&lines[total - tail..].join("\n")); }

        let mut neighborhood = String::new();
        let win = 120usize;
        let start = snip.start_line.saturating_sub(1).saturating_sub(win);
        let end = (snip.end_line + win).min(total);
        neighborhood.push_str(&lines[start..end].join("\n"));

        format!(
            "Filename: {filename}\n\n[FILE CONTENT TRUNCATED]\n{truncated}\n\n[SNIPPET NEIGHBORHOOD]\n{neighborhood}\n\n[SNIPPET META]\nid: {id}\nname: {name}\nkind: {kind}\nlines: {lstart}-{lend}\n\n[SNIPPET CODE]\n{code}\n\n[RESPONSE FORMAT]\nReturn exactly this JSON on one line: {{\"id\":\"{id}\",\"summary\":\"<plain text summary only>\"}}",
            filename=filename,
            truncated=truncated,
            neighborhood=neighborhood,
            id=snip.id,
            name=snip.name,
            kind=snip.kind,
            lstart=snip.start_line,
            lend=snip.end_line,
            code=snip.code
        )
    } else {
        format!(
            "Filename: {filename}\n\n[FILE CONTENT]\n{full}\n\n[SNIPPET META]\nid: {id}\nname: {name}\nkind: {kind}\nlines: {lstart}-{lend}\n\n[SNIPPET CODE]\n{code}\n\n[RESPONSE FORMAT]\nReturn exactly this JSON on one line: {{\"id\":\"{id}\",\"summary\":\"<plain text summary only>\"}}",
            filename=filename,
            full=full_content,
            id=snip.id,
            name=snip.name,
            kind=snip.kind,
            lstart=snip.start_line,
            lend=snip.end_line,
            code=snip.code
        )
    };

    (system, user)
}

// Temporary mock until we wire the actual client
pub fn mock_call_model(_model: &str, _system: &str, user: &str) -> Result<String> {
    // Produce a minimal valid JSON response using the provided id
    let mut id = "snippet".to_string();
    for line in user.lines() {
        if let Some(rest) = line.strip_prefix("id: ") { id = rest.trim().to_string(); break; }
    }
    Ok(format!("{{\"id\":\"{}\",\"summary\":\"placeholder summary\"}}", id))
}


