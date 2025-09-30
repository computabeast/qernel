use anyhow::{Context, Result};
use std::path::Path;
use std::time::Duration;

use crate::cmd::prototype::{
    console::ConsoleStreamer,
    environment::{build_exec_env, normalize_command, resolve_absolute_path},
    logging::{debug_log, init_debug_logging},
    network::{make_openai_request, AiStep},
    prompts::{build_system_prompt, build_user_prompt},
    snapshots::create_directory_snapshot,
    validation::validate_patch_paths,
};

/// Main agent loop - coordinates the AI agent execution
pub fn run_agent_loop(
    cwd: String, 
    goal: String, 
    test_cmd: String, 
    model: String, 
    max_iters: u32, 
    debug: bool
) -> Result<()> {
    let cwd_abs = resolve_absolute_path(&cwd)?;
    std::fs::create_dir_all(&cwd_abs).context("create cwd")?;
    // Ensure all FS mutations happen under the project root.
    std::env::set_current_dir(&cwd_abs).context("chdir to project root")?;

    // Initialize debug logging if enabled
    let debug_file = init_debug_logging(&cwd_abs, debug)?;

    // Note: streaming diffs removed as they're handled directly in console.rs

    // Initialize console streamer
    let console = ConsoleStreamer::new();
    
    // Present the goal in a more elegant way
    console.section("AI Agent Objective")?;
    if debug {
        // Show full content in debug mode
        console.println(&goal)?;
    } else {
        // Show just a summary in normal mode
        console.typewriter("User intent loaded", 15)?;
    }
    console.println("")?;
    let argv: Vec<String> = shlex::split(&test_cmd).unwrap_or_else(|| vec![test_cmd.clone()]);
    if argv.is_empty() { anyhow::bail!("empty test_cmd"); }

    // Minimal AI loop using OpenAI Chat Completions
    let api_key = std::env::var("OPENAI_API_KEY").context("OPENAI_API_KEY not set")?;
    let mut iteration: u32 = 0;
    let mut failure_context = String::new();
    
    loop {
        iteration += 1;
        console.animated_iteration_header(iteration, max_iters)?;

        // Show context size warning if needed
        let system_prompt = build_system_prompt(&goal, &test_cmd, &cwd_abs, &create_directory_snapshot(&cwd_abs).unwrap_or_default());
        let user_prompt = build_user_prompt(&goal, &failure_context);
        let total_context_size = system_prompt.len() + user_prompt.len();
        console.context_size_warning(total_context_size)?;
        
        // Start thinking spinner with timer (10 minute timeout)
        let spinner = console.start_spinner_with_timer("AI is thinking...", 600);
        
        // Ask model for next action
        let suggestion = request_ai_step(&api_key, &model, &goal, &test_cmd, &cwd_abs, &debug_file, &failure_context)?;
        
        // Stop thinking spinner (already stopped in streaming callback, but ensure it's stopped)
        console.stop_spinner(&spinner);
        
        // Add a thoughtful pause
        std::thread::sleep(Duration::from_millis(800));

        match suggestion.action.as_str() {
            "apply_patch" => {
                unsafe { std::env::set_var("QERNEL_TURN_DIFF", "1") };
                let mut stdout = std::io::stdout();
                let mut stderr = std::io::stderr();
                let patch_body = suggestion.patch.clone().unwrap_or_default();
                
                        // Show patch preview
                        console.patch_preview(&patch_body)?;
                        
                        // More thoughtful apply message
                        console.typewriter("Analyzing code changes...", 20)?;
                        std::thread::sleep(Duration::from_millis(500));
                        console.typewriter("Applying modifications...", 20)?;
                
                // Check for empty or invalid patches
                if patch_body.trim() == "*** Begin Patch\n*** End Patch" || 
                   patch_body.trim() == "*** End Patch" ||
                   patch_body.trim().is_empty() {
                    console.error("Rejected empty patch - no changes detected")?;
                        } else if let Err(e) = validate_patch_paths(&patch_body, &cwd_abs) {
                            console.error(&format!("Rejected patch: {}", e))?;
                        } else {
                            // Debug: Log the patch content for troubleshooting
                            debug_log(&debug_file, &format!("[patch] Applying patch:\n{}", patch_body), debug_file.is_some());
                            if let Err(e) = qernel_apply_patch::apply_patch(&patch_body, &mut stdout, &mut stderr) {
                                console.error(&format!("Failed to apply patch: {}", e))?;
                                debug_log(&debug_file, &format!("[patch] Error details: {}", e), debug_file.is_some());
                            } else {
                                console.typewriter("Code changes applied successfully", 15)?;
                            }
                        }
            }
            "shell" => {
                let cmd_s = suggestion.command.clone().unwrap_or_default();
                console.typewriter(&format!("Executing: {}", cmd_s), 15)?;
                std::thread::sleep(Duration::from_millis(300));
                let cmd = if cmd_s.is_empty() { argv.clone() } else { shlex::split(&cmd_s).unwrap_or(argv.clone()) };
                let _ = run_cmd_with_events(&cmd, &cwd_abs)?;
            }
            _ => {
                console.warning(&format!("Unrecognized action: {:?}", suggestion.action))?;
            }
        }

        // Add a thoughtful pause before testing
        console.typewriter("Running tests to verify implementation...", 20)?;
        std::thread::sleep(Duration::from_millis(600));
        
        // Test
        let out = run_cmd_with_events(&argv, &cwd_abs)?;
        
        // Show execution result
        if debug {
            console.debug_execution_result(
                &argv.join(" "),
                out.exit_code,
                &out.stdout.text,
                &out.stderr.text,
            )?;
        } else {
            // Show the actual test output directly
            if !out.stdout.text.is_empty() {
                console.println(&out.stdout.text)?;
            }
            if !out.stderr.text.is_empty() {
                console.println(&out.stderr.text)?;
            }
            
            // Simple pass/fail indicator
            if out.exit_code == 0 {
                console.success("✓ Tests passed!")?;
            } else {
                console.error("✗ Tests failed")?;
            }
        }
        
        // Collect failure context for next iteration
        if !is_success(&out, None) {
            failure_context.clear();
            failure_context.push_str(&format!("Previous iteration {} failed with exit code {}.\n", iteration, out.exit_code));
            
            if !out.stdout.text.is_empty() {
                failure_context.push_str("Test output:\n");
                failure_context.push_str(&out.stdout.text);
                failure_context.push_str("\n");
            }
            
            if !out.stderr.text.is_empty() {
                failure_context.push_str("Error output:\n");
                failure_context.push_str(&out.stderr.text);
                failure_context.push_str("\n");
            }
        }
        
        // Always log debug info to logs file
        if let Some(debug_file) = &debug_file {
            use crate::cmd::prototype::logging::debug_log;
            debug_log(&Some(debug_file.clone()), &format!("[exec] {} (exit={})", &argv.join(" "), out.exit_code), false);
            if !out.stdout.text.is_empty() {
                debug_log(&Some(debug_file.clone()), &format!("stdout:\n{}", out.stdout.text), false);
            }
            if !out.stderr.text.is_empty() {
                debug_log(&Some(debug_file.clone()), &format!("stderr:\n{}", out.stderr.text), false);
            }
        }
        
        if is_success(&out, None) {
            console.println("")?;
            console.success("🎉 Implementation completed successfully!")?;
            break Ok(());
        }

        if iteration >= max_iters { 
            console.println("")?;
            console.error("⚠️  Maximum iterations reached without success")?;
            anyhow::bail!("max iters reached without success") 
        }

        // Ask user for confirmation before next iteration
        if iteration < max_iters {
            console.println("")?;
            let should_continue = console.ask_continue(&format!(
                "Iteration {} completed. Tests are still failing. Would you like the AI agent to continue with iteration {}?",
                iteration, iteration + 1
            ))?;
            
            if !should_continue {
                console.info("User chose to stop. Exiting...")?;
                break Ok(());
            }
        }
    }
}


/// Request AI step with focused context and clear instructions
fn request_ai_step(api_key: &str, model: &str, goal: &str, test_cmd: &str, cwd: &Path, debug_file: &Option<std::path::PathBuf>, failure_context: &str) -> Result<AiStep> {
    // Create focused directory snapshot
    let project_directory_content = create_directory_snapshot(cwd)
        .unwrap_or_else(|_| "Failed to read project directory".to_string());
    
    // Cap prompt size to keep requests reasonable
    const MAX_CTX: usize = 120_000;
    let project_directory_content = if project_directory_content.len() > MAX_CTX {
        let head = &project_directory_content[..MAX_CTX / 2];
        let tail = &project_directory_content[project_directory_content.len() - MAX_CTX / 2..];
        format!("{head}\n...\n[TRUNCATED]\n...\n{tail}")
    } else {
        project_directory_content
    };
    
    // Debug: Show what context the agent is receiving
    debug_log(debug_file, &format!("[ai] project directory content length: {} chars", project_directory_content.len()), debug_file.is_some());
    debug_log(debug_file, &format!("[ai] project directory preview: {}", &project_directory_content[..project_directory_content.len().min(500)]), debug_file.is_some());
    debug_log(debug_file, &format!("[ai] model: {}", model), debug_file.is_some());
    
    // Show the complete project context that the model sees
    debug_log(debug_file, "[ai] ===== COMPLETE PROJECT CONTEXT =====", false);
    debug_log(debug_file, &project_directory_content, false);
    debug_log(debug_file, "[ai] ===== END PROJECT CONTEXT =====", false);

    let system = build_system_prompt(goal, test_cmd, cwd, &project_directory_content);
    let user = build_user_prompt(goal, failure_context);
    
    // Debug: Show prompt lengths
    debug_log(debug_file, &format!("[ai] system prompt length: {} chars", system.len()), debug_file.is_some());
    debug_log(debug_file, &format!("[ai] user prompt length: {} chars", user.len()), debug_file.is_some());
    
    // Show the complete system prompt that the model sees
    debug_log(debug_file, "[ai] ===== COMPLETE SYSTEM PROMPT =====", false);
    debug_log(debug_file, &system, false);
    debug_log(debug_file, "[ai] ===== END SYSTEM PROMPT =====", false);
    
    // Show the complete user prompt that the model sees
    debug_log(debug_file, "[ai] ===== COMPLETE USER PROMPT =====", false);
    debug_log(debug_file, &user, false);
    debug_log(debug_file, "[ai] ===== END USER PROMPT =====", false);

    // Create tools for the request
    let tools = create_tools(model);
    
    // Use simple non-streaming request
    make_openai_request(api_key, model, &system, &user, tools, debug_file)
}

fn create_tools(model: &str) -> serde_json::Value {
    use qernel_codex_core::tool_apply_patch::{
        create_apply_patch_freeform_tool,  // "custom" (free-form / grammar) — GPT-5 only
        create_apply_patch_json_tool,      // "function" (JSON schema)
    };
    
    let use_custom_tools = model.starts_with("gpt-5"); // e.g., "gpt-5-codex"
    
    if use_custom_tools {
        // GPT-5 models use custom freeform tools
        serde_json::to_value(vec![create_apply_patch_freeform_tool()]).expect("tools json")
    } else {
        // codex-mini-latest and other models use JSON function tools
        serde_json::to_value(vec![create_apply_patch_json_tool()]).expect("tools json")
    }
}

// Exec helper with live event printing
fn run_cmd_with_events(argv: &[String], cwd: &Path) -> Result<qernel_codex_core::exec::ExecToolCallOutput> {
    use async_channel::unbounded as async_unbounded;
    use qernel_codex_core::exec::{process_exec_tool_call, ExecParams, SandboxType, StdoutStream};
    use qernel_codex_core::protocol::{Event, SandboxPolicy};

    let cmd = normalize_command(argv);
    let params = ExecParams {
        command: cmd,
        cwd: cwd.to_path_buf(),
        timeout_ms: Some(120_000), // Tests can reasonable take longer
        env: build_exec_env(cwd),
        with_escalated_permissions: None,
        justification: None,
    };

    let rt = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .context("failed to create tokio runtime")?;

    let (tx_event, rx_event) = async_unbounded::<Event>();
            std::thread::spawn(move || {
                while let Ok(_ev) = rx_event.recv_blocking() {
                    // Event handling - no output needed
                }
            });

    let stream = StdoutStream {
        sub_id: "s1".into(),
        call_id: "c1".into(),
        tx_event: tx_event.clone(),
    };

    let out = rt
        .block_on(process_exec_tool_call(
            params,
            SandboxType::None,
            &SandboxPolicy::DANGER_FULL_ACCESS,
            &std::path::PathBuf::from("/"),
            &None,
            Some(stream),
        ))
        .map_err(|e| anyhow::anyhow!("exec error: {:?}", e))?;
    Ok(out)
}

fn is_success(out: &qernel_codex_core::exec::ExecToolCallOutput, must_contain: Option<&str>) -> bool {
    let code_ok = out.exit_code == 0;
    if !code_ok { return false; }
    match must_contain {
        Some(s) => out.stdout.text.to_lowercase().contains(&s.to_lowercase()),
        None => true,
    }
}
