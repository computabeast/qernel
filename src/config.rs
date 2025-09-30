use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use anyhow::Context;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QernelConfig {
    pub project: ProjectConfig,
    pub agent: AgentConfig,
    pub papers: Vec<PaperConfig>,
    pub content_files: Option<Vec<String>>,
    pub benchmarks: BenchmarkConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectConfig {
    pub name: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    pub model: String,
    pub max_iterations: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaperConfig {
    pub url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkConfig {
    pub test_command: String,
}

impl Default for QernelConfig {
    fn default() -> Self {
        Self {
            project: ProjectConfig {
                name: "qernel-project".to_string(),
                description: "A qernel prototype project".to_string(),
            },
            agent: AgentConfig {
                model: "gpt-5-codex".to_string(),
                max_iterations: 15,
            },
            papers: Vec::new(),
            content_files: None,
            benchmarks: BenchmarkConfig {
                test_command: "python -m pytest src/tests.py -v".to_string(),
            },
        }
    }
}

pub fn load_config(config_path: &PathBuf) -> anyhow::Result<QernelConfig> {
    if !config_path.exists() {
        return Ok(QernelConfig::default());
    }
    
    let content = std::fs::read_to_string(config_path)
        .context("Failed to read qernel.yaml")?;
    
    let config: QernelConfig = serde_yaml::from_str(&content)
        .context("Failed to parse qernel.yaml")?;
    
    Ok(config)
}

pub fn save_config(config: &QernelConfig, config_path: &PathBuf) -> anyhow::Result<()> {
    let content = serde_yaml::to_string(config)
        .context("Failed to serialize config")?;
    
    std::fs::write(config_path, content)
        .context("Failed to write qernel.yaml")?;
    
    Ok(())
}
