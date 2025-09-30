use qernel_codex_core::exec::{process_exec_tool_call, ExecParams, SandboxType, StdoutStream};
use qernel_codex_core::protocol::SandboxPolicy;
use std::collections::HashMap;
use std::path::PathBuf;

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn smoke_exec_echo_and_curl() {
    // 1) Echo "hello"
    let params = ExecParams {
        command: vec!["/bin/echo".into(), "hello".into()],
        cwd: std::env::current_dir().unwrap(),
        timeout_ms: Some(5_000),
        env: HashMap::new(),
        with_escalated_permissions: None,
        justification: None,
    };
    let out = process_exec_tool_call(
        params,
        SandboxType::None,
        &SandboxPolicy::DANGER_FULL_ACCESS,
        &PathBuf::from("/"),
        &None,
        None::<StdoutStream>,
    )
    .await
    .expect("echo failed");
    assert_eq!(out.exit_code, 0);
    assert!(out.stdout.text.contains("hello"));

    // 2) Fetch a small page (web fetch via shell path)
    let curl = which::which("curl").expect("curl not found");
    let tmpdir = tempfile::tempdir().unwrap();
    let out_file = tmpdir.path().join("example.html");
    let params = ExecParams {
        command: vec![
            curl.to_string_lossy().to_string(),
            "-L".into(),
            "https://example.com/".into(),
            "-o".into(),
            out_file.to_string_lossy().to_string(),
        ],
        cwd: std::env::current_dir().unwrap(),
        timeout_ms: Some(10_000),
        env: HashMap::new(),
        with_escalated_permissions: None,
        justification: None,
    };
    let out = process_exec_tool_call(
        params,
        SandboxType::None,
        &SandboxPolicy::DANGER_FULL_ACCESS,
        &PathBuf::from("/"),
        &None,
        None::<StdoutStream>,
    )
    .await
    .expect("curl failed");
    assert_eq!(out.exit_code, 0);
    let body = std::fs::read_to_string(&out_file).expect("read fetched file");
    assert!(body.contains("Example Domain"));
}

#[tokio::test(flavor = "multi_thread", worker_threads = 2)]
async fn smoke_unified_exec_persists() {
    use qernel_codex_core::unified_exec::{UnifiedExecRequest, UnifiedExecSessionManager};

    let manager = UnifiedExecSessionManager::default();

    // Open interactive bash session
    let open_shell = manager
        .handle_request(UnifiedExecRequest {
            session_id: None,
            input_chunks: &["/bin/bash".to_string(), "-i".to_string()],
            timeout_ms: Some(2_500),
        })
        .await
        .expect("open bash session");
    let session_id = open_shell.session_id.expect("expected session id");

    // Set env var within the session
    manager
        .handle_request(UnifiedExecRequest {
            session_id: Some(session_id),
            input_chunks: &["export CODEX_INTERACTIVE_SHELL_VAR=codex\n".to_string()],
            timeout_ms: Some(2_500),
        })
        .await
        .expect("export variable");

    // Echo it and verify persistence
    let out = manager
        .handle_request(UnifiedExecRequest {
            session_id: Some(session_id),
            input_chunks: &["echo $CODEX_INTERACTIVE_SHELL_VAR\n".to_string()],
            timeout_ms: Some(2_500),
        })
        .await
        .expect("echo variable");
    assert!(out.output.contains("codex"));
}


