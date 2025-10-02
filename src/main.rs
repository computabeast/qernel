mod cmd;
mod config;
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
    /// Authenticate with the Zoo by saving and inspecting your personal access token
    Auth,
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
        /// Max iterations for AI loop
        #[arg(long, default_value_t = 15)]
        max_iters: u32,
        /// Enable debug logging to .logs file
        #[arg(long)]
        debug: bool,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::New { path, template } => cmd::new::handle_new(path, template),
        Commands::Auth => cmd::login::handle_auth(),
        Commands::Push { remote, url, branch, no_commit } => cmd::push::handle_push(remote, url, branch, no_commit),
        Commands::Pull { repo, dest, branch, server } => cmd::pull::handle_pull(repo, dest, branch, server),
        Commands::Prototype { cwd, model, max_iters, debug } => cmd::prototype::handle_prototype(cwd, model, max_iters, debug),
    }
}