mod cmd;
mod util;

use anyhow::Result;
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "qernel", version, about = "Lightweight quantum CLI", long_about = None)]
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
        /// Initialize with a default template structure
        #[arg(long, default_value_t = true, action = clap::ArgAction::SetTrue)]
        template: bool,
    },
    /// Login by saving personal access token
    Login,
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
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.command {
        Commands::New { path, template } => cmd::new::handle_new(path, template),
        Commands::Login => cmd::login::handle_login(),
        Commands::Push { remote, url, branch } => cmd::push::handle_push(remote, url, branch),
    }
}
