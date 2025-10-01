use anyhow::Result;
use std::path::Path;

/// Create a focused directory snapshot containing only the essential project files
pub fn create_directory_snapshot(project_root: &Path) -> Result<String> {
    let mut snapshot = String::new();
    
    // Add essential config files
    let config_files = [
        ("benchmark.md", "Benchmarking criteria"),
        ("requirements.txt", "Python dependencies"),
    ];
    
    for (filename, description) in &config_files {
        let file_path = project_root.join(filename);
        if file_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&file_path) {
                snapshot.push_str(&format!("=== {} ({}) ===\n", filename, description));
                snapshot.push_str(&content);
                snapshot.push_str("\n\n");
            }
        }
    }
    
    // Add Python files from src/ directory only
    let src_path = project_root.join("src");
    if src_path.exists() {
        snapshot.push_str("=== Python source files ===\n");
        read_python_files(&src_path, &mut snapshot, project_root)?;
    }
    
    // Add parsed images information if available
    add_parsed_images_info(&mut snapshot, project_root)?;
    
    Ok(snapshot)
}

/// Helper function to read only Python files from directory recursively
pub fn read_python_files(dir: &std::path::Path, contents: &mut String, project_root: &std::path::Path) -> std::io::Result<()> {
    if dir.is_dir() {
        let mut entries = std::fs::read_dir(dir)?.collect::<Result<Vec<_>, _>>()?;
        entries.sort_by_key(|e| e.path());
        for entry in entries {
            let path = entry.path();
            let name = path.file_name().unwrap_or_default().to_string_lossy();
            
            // Skip common build artifacts and cache directories
            if name == "__pycache__"
                || name == ".git"
                || name == ".qernel"
                || name == "node_modules"
                || name == "target"
                || name == "build"
                || name == "dist"
                || name == ".pytest_cache"
                || name == ".mypy_cache"
                || name.ends_with(".pyc")
            {
                continue;
            }
            
            let rel = path.strip_prefix(project_root).unwrap_or(&path).to_string_lossy().to_string();
            
            if path.is_dir() {
                // Recursively read subdirectories
                read_python_files(&path, contents, project_root)?;
            } else if name.ends_with(".py") {
                // Only read Python files
                contents.push_str(&format!("=== {} ===\n", rel));
                match std::fs::read_to_string(&path) {
                    Ok(file_content) => contents.push_str(&file_content),
                    Err(_) => contents.push_str("[Binary file or read error]\n"),
                }
                contents.push('\n');
            }
        }
    }
    Ok(())
}

/// Add information about parsed images to the snapshot
fn add_parsed_images_info(snapshot: &mut String, project_root: &Path) -> Result<()> {
    let qernel_dir = project_root.join(".qernel");
    let parsed_dir = qernel_dir.join("parsed");
    
    if !parsed_dir.exists() {
        return Ok(());
    }
    
    // Find all images directories in parsed folders
    let mut images_found = false;
    
    if let Ok(entries) = std::fs::read_dir(&parsed_dir) {
        for entry in entries {
            let entry = entry?;
            let path = entry.path();
            
            if path.is_dir() {
                let images_dir = path.join("images");
                if images_dir.exists() {
                    if !images_found {
                        snapshot.push_str("=== Parsed Images ===\n");
                        images_found = true;
                    }
                    
                    // Get the folder name (e.g., "arxiv_9605021")
                    let folder_name = path.file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("unknown");
                    
                    snapshot.push_str(&format!("**Folder: {}**\n", folder_name));
                    
                    // List images in this folder
                    if let Ok(image_entries) = std::fs::read_dir(&images_dir) {
                        let mut image_count = 0;
                        for image_entry in image_entries {
                            let image_path = image_entry?.path();
                            if image_path.is_file() {
                                if let Some(extension) = image_path.extension() {
                                    if let Some(ext_str) = extension.to_str() {
                                        if matches!(ext_str.to_lowercase().as_str(), "jpg" | "jpeg" | "png" | "gif" | "bmp" | "webp") {
                                            image_count += 1;
                                        }
                                    }
                                }
                            }
                        }
                        snapshot.push_str(&format!("  - {} images available\n", image_count));
                        snapshot.push_str(&format!("  - Path: {}\n", images_dir.strip_prefix(project_root).unwrap_or(&images_dir).display()));
                    }
                    snapshot.push_str("\n");
                }
            }
        }
    }
    
    if images_found {
        snapshot.push_str("**Note**: Use the `view_image` tool to examine specific images when needed.\n\n");
    }
    
    Ok(())
}
