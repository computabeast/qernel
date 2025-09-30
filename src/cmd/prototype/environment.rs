use anyhow::Result;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

/// Build execution environment with virtual environment support
pub fn build_exec_env(project_root: &Path) -> HashMap<String, String> {
    let mut env: HashMap<String, String> = std::env::vars().collect();
    let venv = project_root.join(".qernel").join(".venv");
    let bin = if cfg!(windows) { venv.join("Scripts") } else { venv.join("bin") };

    if bin.is_dir() {
        let sep = if cfg!(windows) { ';' } else { ':' };
        let old = env.get("PATH").cloned().unwrap_or_default();
        env.insert("PATH".into(),
            if old.is_empty() { bin.display().to_string() } else { format!("{}{}{}", bin.display(), sep, old) }
        );
        env.insert("VIRTUAL_ENV".into(), venv.display().to_string());
        env.insert("PIP_DISABLE_PIP_VERSION_CHECK".into(), "1".into());
    }
    env
}

/// Use virtual environment Python if available, otherwise fallback to system python.
pub fn normalize_command(argv: &[String]) -> Vec<String> {
    if argv.is_empty() { return vec![]; }
    let mut out = argv.to_vec();
    
    // If the command is 'python', try to use the virtual environment Python first
    if out[0] == "python" {
        // Check if we're in a project with a virtual environment
        if let Some(project_root) = find_project_root() {
            let venv_python = if cfg!(windows) {
                project_root.join(".qernel").join(".venv").join("Scripts").join("python.exe")
            } else {
                project_root.join(".qernel").join(".venv").join("bin").join("python")
            };
            
            if venv_python.exists() {
                out[0] = venv_python.to_string_lossy().to_string();
                return out;
            }
        }
        
        // Fallback to system python3 if python is not found
        if which_in_path("python").is_none() && which_in_path("python3").is_some() {
            println!("[exec] 'python' not found, using 'python3'");
            out[0] = "python3".to_string();
        }
    }
    out
}

pub fn which_in_path(cmd: &str) -> Option<PathBuf> {
    use std::ffi::OsString;
    let path: OsString = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path) {
        let candidate = dir.join(cmd);
        if candidate.is_file() {
            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                if std::fs::metadata(&candidate).ok()?.permissions().mode() & 0o111 != 0 {
                    return Some(candidate);
                }
            }
            #[cfg(not(unix))]
            {
                return Some(candidate);
            }
        }
    }
    None
}

pub fn resolve_absolute_path(p: &str) -> Result<PathBuf> {
    let path = Path::new(p);
    let abs = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()?.join(path)
    };
    Ok(abs.canonicalize().unwrap_or(abs))
}

/// Find the project root by looking for qernel.yaml or .qernel directory
fn find_project_root() -> Option<PathBuf> {
    let mut current = std::env::current_dir().ok()?;
    
    loop {
        // Check if this directory contains qernel.yaml or .qernel
        if current.join("qernel.yaml").exists() || current.join(".qernel").exists() {
            return Some(current);
        }
        
        // Move up one directory
        if let Some(parent) = current.parent() {
            current = parent.to_path_buf();
        } else {
            break;
        }
    }
    
    None
}
