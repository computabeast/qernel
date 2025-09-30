use std::collections::HashMap;
use std::path::PathBuf;
use std::time::Duration;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FileChange {
    Add { content: String },
    Delete,
    Update { unified_diff: String, move_path: Option<PathBuf> },
}

// Minimal stubs used by exec/shell signatures only for compilation.
#[allow(dead_code)]
#[derive(Debug, Clone)]
pub enum ExecOutputStream { Stdout, Stderr }

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct ExecCommandOutputDeltaEvent {
    pub call_id: String,
    pub stream: ExecOutputStream,
    pub chunk: Vec<u8>,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct ExecCommandBeginEvent {
    pub call_id: String,
    pub command: String,
    pub cwd: PathBuf,
    pub parsed_cmd: Vec<String>,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct ExecCommandEndEvent {
    pub call_id: String,
    pub stdout: String,
    pub stderr: String,
    pub aggregated_output: String,
    pub exit_code: i32,
    pub duration: Duration,
    pub formatted_output: String,
}

// FileChange already defined above for apply-patch interop

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct PatchApplyBeginEvent {
    pub call_id: String,
    pub auto_approved: bool,
    pub changes: HashMap<PathBuf, FileChange>,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct PatchApplyEndEvent {
    pub call_id: String,
    pub stdout: String,
    pub stderr: String,
    pub success: bool,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct TurnDiffEvent {
    pub unified_diff: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct ErrorEvent {
    pub message: String,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub enum EventMsg {
    ExecCommandOutputDelta(ExecCommandOutputDeltaEvent),
    ExecCommandBegin(ExecCommandBeginEvent),
    ExecCommandEnd(ExecCommandEndEvent),
    PatchApplyBegin(PatchApplyBeginEvent),
    PatchApplyEnd(PatchApplyEndEvent),
    TurnDiff(TurnDiffEvent),
    Error(ErrorEvent),
    ShutdownComplete,
}

#[allow(dead_code)]
#[derive(Debug, Clone)]
pub struct Event { pub id: String, pub msg: EventMsg }

#[allow(dead_code)]
#[derive(Debug, Clone, Copy)]
pub struct SandboxPolicy;

impl SandboxPolicy {
    pub const DANGER_FULL_ACCESS: SandboxPolicy = SandboxPolicy;
    pub fn has_full_network_access(&self) -> bool { true }
}


