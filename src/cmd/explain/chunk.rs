use anyhow::Result;
use std::path::Path;
use tree_sitter::{Node, Parser};
use tree_sitter_python as tspy;

#[derive(Clone, Copy, Debug)]
pub enum ChunkGranularity { Function, Class, Block }

#[derive(Clone, Debug)]
pub struct PythonChunk {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub start_line: usize,
    pub end_line: usize,
    pub code: String,
}

pub fn chunk_python_or_fallback(content: &str, path: &Path, granularity: ChunkGranularity) -> Result<Vec<PythonChunk>> {
    let filename = path.file_name().and_then(|s| s.to_str()).unwrap_or("<file>");
    // Try AST-based parsing first
    if let Ok(ast_chunks) = chunk_python_ast(content, filename, granularity) {
        if !ast_chunks.is_empty() { return Ok(ast_chunks); }
    }
    // Heuristic fallback
    let mut chunks: Vec<PythonChunk> = Vec::new();
    let mut lines = content.lines().enumerate().peekable();
    let mut idx: usize = 0;
    while let Some((i, line)) = lines.next() {
        let trimmed = line.trim_start();
        let is_def = trimmed.starts_with("def ") || trimmed.starts_with("async def ");
        let is_class = trimmed.starts_with("class ");
        let capture = match granularity {
            ChunkGranularity::Function => is_def,
            ChunkGranularity::Class => is_class,
            ChunkGranularity::Block => is_def || is_class,
        };
        if !capture { continue; }

        let start = i + 1; // 1-based lines
        // Find end based on indentation drop or EOF
        let indent_prefix = line.chars().take_while(|c| *c == ' ' || *c == '\t').collect::<String>();
        let mut lookahead_index = i;
        while let Some(&(j, ref l)) = lines.peek() {
            let t = l.trim();
            let this_indent = l.chars().take_while(|c| *c == ' ' || *c == '\t').collect::<String>();
            if !t.is_empty() && this_indent.len() <= indent_prefix.len() && (t.starts_with("def ") || t.starts_with("class ") || t.starts_with("async def ")) {
                break;
            }
            lookahead_index = j;
            lines.next();
        }
        let end = lookahead_index + 1;

        let code = content
            .lines()
            .skip(start - 1)
            .take(end - start + 1)
            .collect::<Vec<_>>()
            .join("\n");

        // Name extraction
        let name = if is_class {
            trimmed.trim_start_matches("class ").split('(').next().unwrap_or("").trim().trim_end_matches(':').to_string()
        } else {
            let rest = if trimmed.starts_with("async def ") { &trimmed[10..] } else { trimmed.trim_start_matches("def ") };
            rest.split('(').next().unwrap_or("").trim().to_string()
        };

        let kind = if is_class { "class" } else { "function" }.to_string();
        idx += 1;
        let id = format!("{}::{}:{}", filename, kind, idx);
        chunks.push(PythonChunk { id, name, kind, start_line: start, end_line: end, code });
    }

    if chunks.is_empty() {
        // Fallback: whole file as one block
        let total = content.lines().count();
        chunks.push(PythonChunk {
            id: format!("{}::block:1", filename),
            name: filename.to_string(),
            kind: "block".to_string(),
            start_line: 1,
            end_line: total,
            code: content.to_string(),
        });
    }

    Ok(chunks)
}

fn chunk_python_ast(content: &str, filename: &str, granularity: ChunkGranularity) -> Result<Vec<PythonChunk>> {
    let mut parser = Parser::new();
    parser.set_language(&tspy::language()).expect("load python grammar");
    let tree = parser.parse(content, None).ok_or_else(|| anyhow::anyhow!("failed to parse python"))?;
    let root = tree.root_node();

    let mut chunks: Vec<PythonChunk> = Vec::new();

    //

    let mut idx_fn = 0usize;
    let mut idx_cls = 0usize;

    // Traverse top-level and nested definitions
    let mut cursor = root.walk();
    for child in root.children(&mut cursor) {
        collect_defs(content, filename, child, granularity, &mut idx_fn, &mut idx_cls, &mut chunks);
    }

    Ok(chunks)
}

fn collect_defs(content: &str, filename: &str, node: Node, granularity: ChunkGranularity, idx_fn: &mut usize, idx_cls: &mut usize, chunks: &mut Vec<PythonChunk>) {
    let kind = node.kind();
    match kind {
        "function_definition" | "async_function_definition" => {
            if matches!(granularity, ChunkGranularity::Function | ChunkGranularity::Block) {
                *idx_fn += 1;
                let name = node
                    .child_by_field_name("name")
                    .and_then(|n| Some(n.utf8_text(content.as_bytes()).unwrap_or("").to_string()))
                    .unwrap_or_else(|| "<lambda>".to_string());
                let range = node.range();
                let start = range.start_point.row + 1;
                let end = range.end_point.row + 1;
                let code = slice_lines(content, start, end);
                let id = format!("{}::function:{}", filename, *idx_fn);
                chunks.push(PythonChunk { id, name, kind: "function".to_string(), start_line: start, end_line: end, code });
            }
        }
        "class_definition" => {
            if matches!(granularity, ChunkGranularity::Class | ChunkGranularity::Block) {
                *idx_cls += 1;
                let name = node
                    .child_by_field_name("name")
                    .and_then(|n| Some(n.utf8_text(content.as_bytes()).unwrap_or("").to_string()))
                    .unwrap_or_else(|| "<class>".to_string());
                let range = node.range();
                let start = range.start_point.row + 1;
                let end = range.end_point.row + 1;
                let code = slice_lines(content, start, end);
                let id = format!("{}::class:{}", filename, *idx_cls);
                chunks.push(PythonChunk { id, name, kind: "class".to_string(), start_line: start, end_line: end, code });
            }
        }
        _ => {}
    }

    // Recurse into children
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        collect_defs(content, filename, child, granularity, idx_fn, idx_cls, chunks);
    }
}

fn slice_lines(content: &str, start: usize, end: usize) -> String {
    content.lines().skip(start - 1).take(end - start + 1).collect::<Vec<_>>().join("\n")
}


