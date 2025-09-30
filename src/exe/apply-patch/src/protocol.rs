use std::path::PathBuf;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FileChange {
    Add { content: String },
    Delete,
    Update { unified_diff: String, move_path: Option<PathBuf> },
}


