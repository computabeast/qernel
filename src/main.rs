mod cmd;
mod config;
pub mod common;
mod util;

use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "qernel", version, about = "Lightweight quantum CLI", long_about = None, disable_help_subcommand = true)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Create a new qernel repo with scaffolded structure
    New {
        /// Project directory to create
        path: String,
        /// Initialize with prototype template
        #[arg(long)]
        template: bool,
    },
    /// Authenticate with the Zoo and manage local OpenAI API key
    Auth {
        /// Set and save an OpenAI API key (reads from stdin if empty prompt)
        #[arg(long)]
        set_openai_key: bool,
        /// Remove any stored OpenAI API key from local config
        #[arg(long)]
        unset_openai_key: bool,
    },
    /// Push current repo to remote server
    Push {
        /// Optional remote name (default: origin)
        #[arg(long, default_value = "origin")]
        remote: String,
        /// Optional remote url; if provided, sets/updates remote
        #[arg(long)]
        url: Option<String>,
        /// Branch to push (default: current)
        #[arg(long)]
        branch: Option<String>,
        /// Skip auto-commit of changes
        #[arg(long)]
        no_commit: bool,
    },
    /// Pull (clone) a repo from server or full URL
    Pull {
        /// Repo path or full URL. If not a URL, it will be joined to the server base.
        repo: String,
        /// Destination directory to clone into
        dest: String,
        /// Optional branch to checkout after clone
        #[arg(long)]
        branch: Option<String>,
        /// Server base URL when repo is not a full URL
        #[arg(long, default_value = "https://dojoservice.onrender.com/")]
        server: String,
    },
    /// Run prototype implementation with AI agent
    Prototype {
        /// Working directory
        #[arg(long, default_value = ".")]
        cwd: String,
        /// OpenAI model to use (e.g., gpt-4o-mini)
        #[arg(long, default_value = "gpt-5-codex")]
        model: String,
        /// Run preflight checks and exit
        #[arg(long)]
        check: bool,
        /// Max iterations for AI loop
        #[arg(long, default_value_t = 15)]
        max_iters: u32,
        /// Enable debug logging to .logs file
        #[arg(long)]
        debug: bool,
        /// Use existing .qernel/spec.md only (skip papers and content_files processing)
        #[arg(long)]
        spec_only: bool,
        /// Use .qernel/spec.md and content_files only (skip papers processing)
        #[arg(long)]
        spec_and_content_only: bool,
        /// One-shot prototype an arXiv paper URL (creates new project arxiv-<id>)
        #[arg(long)]
        arxiv: Option<String>,
    },
    /// Explain Python source files with snippet-level analysis
    Explain {
        /// One or more files to explain
        files: Vec<String>,
        /// Granularity: function | class | block (default: function)
        #[arg(long, default_value = "function")]
        per: String,
        /// Optional model override (defaults resolved from YAML or tool config)
        #[arg(long)]
        model: Option<String>,
        /// Run preflight checks and exit
        #[arg(long)]
        check: bool,
        /// Emit Markdown to .qernel/explain or to --output if provided
        #[arg(long)]
        markdown: bool,
        /// Output markdown file or directory for reports
        #[arg(long)]
        output: Option<String>,
        /// Disable paging (default: pager on)
        #[arg(long)]
        no_pager: bool,
        /// Max characters per explanation
        #[arg(long)]
        max_chars: Option<usize>,
    },
    /// Provider operations: show and set provider/base URL
    Provider {
        /// Show current provider configuration
        #[arg(long)]
        show: bool,
        /// List available providers
        #[arg(long)]
        list: bool,
        /// Run a preflight check for the current or specified model
        #[arg(long)]
        check: bool,
        /// Optional model to check
        #[arg(long)]
        model: Option<String>,
        /// Set provider: openai | ollama
        #[arg(long)]
        set: Option<String>,
        /// Set Ollama base URL (e.g., http://localhost:11434/v1)
        #[arg(long)]
        base_url: Option<String>,
        /// Set model for a specific command: prototype | explain
        #[arg(long)]
        set_for_cmd: Option<String>,
        /// Optional positional model to use with --set-for-cmd
        cmd_model: Option<String>,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::New { path, template } => cmd::new::handle_new(path, template),
        Commands::Auth { set_openai_key, unset_openai_key } => cmd::login::handle_auth_with_flags(set_openai_key, unset_openai_key),
        Commands::Push { remote, url, branch, no_commit } => cmd::push::handle_push(remote, url, branch, no_commit),
        Commands::Pull { repo, dest, branch, server } => cmd::pull::handle_pull(repo, dest, branch, server),
        Commands::Prototype { cwd, model, check, max_iters, debug, spec_only, spec_and_content_only, arxiv } => {
            if check { cmd::prototype::check_prototype(cwd, model) } else if let Some(url) = arxiv { cmd::prototype::quickstart_arxiv(url, model, max_iters, debug) } else { cmd::prototype::handle_prototype(cwd, model, max_iters, debug, spec_only, spec_and_content_only) }
        }
        Commands::Explain { files, per, model, check, markdown, output, no_pager, max_chars } => {
            if check { cmd::explain::check_explain(files, model) } else { cmd::explain::handle_explain(files, per, model, markdown, output, !no_pager, max_chars) }
        }
        Commands::Provider { show, list, set, base_url, check, model, set_for_cmd, cmd_model } => {
            cmd::provider::handle_provider(cmd::provider::ProviderCmd { show, list, set, base_url, check, model, set_for_cmd, cmd_model })
        }
    }
}