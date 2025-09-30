use anyhow::Result;
use std::path::PathBuf;

/// Initialize debug logging if enabled
pub fn init_debug_logging(cwd: &std::path::Path, debug: bool) -> Result<Option<PathBuf>> {
    if debug {
        let debug_path = cwd.join(".logs");
        std::fs::write(&debug_path, format!("=== Qernel Debug Log - {}\n\n", chrono::Utc::now().format("%Y-%m-%d %H:%M:%S UTC"))).ok();
        Ok(Some(debug_path))
    } else {
        Ok(None)
    }
}

/// Helper function to write debug logs to file and optionally print to console
pub fn debug_log(debug_file: &Option<PathBuf>, message: &str, print_to_console: bool) {
    if print_to_console {
        println!("{}", message);
    }
    
    if let Some(path) = debug_file {
        if let Ok(mut content) = std::fs::read_to_string(path) {
            content.push_str(message);
            content.push('\n');
            let _ = std::fs::write(path, content);
        }
    }
}

