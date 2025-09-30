use anyhow::Result;
use std::path::Path;

/// Ensure patch file paths are project-relative, cannot escape the root, and are restricted to src/ directory.
pub fn validate_patch_paths(patch: &str, project_root: &Path) -> Result<()> {
    for line in patch.lines() {
        let path_opt = line
            .strip_prefix("*** Add File: ")
            .or_else(|| line.strip_prefix("*** Update File: "))
            .or_else(|| line.strip_prefix("*** Delete File: "))
            .or_else(|| line.strip_prefix("*** Move to: "));
        if let Some(raw) = path_opt {
            let raw = raw.trim();
            let p = Path::new(raw);
            // absolute (incl. Windows drive letters) or parent traversals are forbidden
            if p.is_absolute() || raw.contains(':') {
                anyhow::bail!("absolute path not allowed in patch: {raw}");
            }
            if p.components().any(|c| matches!(c, std::path::Component::ParentDir)) {
                anyhow::bail!("parent traversal not allowed in patch: {raw}");
            }
            // Resolve and confirm it stays under project_root
            let resolved = project_root.join(p).canonicalize().unwrap_or(project_root.join(p));
            if !resolved.starts_with(project_root) {
                anyhow::bail!("path escapes project root: {raw}");
            }
            // Restrict changes to src/main.py only
            if p.to_string_lossy() != "src/main.py" {
                anyhow::bail!("only src/main.py can be modified: {raw}");
            }
        }
    }
    Ok(())
}
