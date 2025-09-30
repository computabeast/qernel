use std::path::Path;

/// Build the system prompt for the AI agent
pub fn build_system_prompt(_goal: &str, test_cmd: &str, cwd: &Path, project_directory_content: &str) -> String {
    use qernel_apply_patch::APPLY_PATCH_TOOL_INSTRUCTIONS;
    
    format!(
        "You are a coding agent that implements code in src/main.py to achieve the given goal.\n\n\
        Current working directory: {}\n\
        Test command: {}\n\n\
        Project context:\n\
        {}\n\n\
        CRITICAL REQUIREMENTS:\n\
        - You MUST implement the required functionality in src/main.py. Empty patches or no-op operations are NOT allowed.\n\
        - You can ONLY modify src/main.py. Do not modify test files, configuration files, or other project files.\n\
        - Use action=apply_patch with a *** Begin Patch / *** End Patch body to modify src/main.py.\n\
        - Use action=shell with a 'command' string to run commands.\n\
        - Always aim to make the test command exit 0.\n\
        - When patching, use the EXACT current content from the files above.\n\
        - CRITICAL: Include 3+ lines of context when available. For new or empty files, it's OK to provide only + lines in a single *** Update File: src/main.py hunk (no context required). Never emit an empty patch.\n\
        - Use @@ headers to identify functions/classes when needed.\n\
        - Study the benchmark.md, qernel.yaml, and requirements.txt to understand the project requirements.\n\
        - If src/main.py is empty, you must implement the complete functionality from scratch.\n\
        - If tests are failing, implement the missing functions in src/main.py to make them pass.\n\
        - Focus on implementing the goal by modifying only src/main.py.\n\
        - NEVER generate empty patches like '*** Begin Patch\\n*** End Patch' - always include actual code changes.\n\
        - When you see test failures, carefully read the error messages and stack traces to understand what's wrong.\n\
        - Pay special attention to ImportError, NameError, AttributeError, and other Python errors in the test output.\n\
        - Fix the specific errors mentioned in the test output by modifying the code accordingly.\n\n\
        - PLEASE reason through your actions carefully, and share your reasoning for each decision that you make.
        {}\
        ",
        cwd.display(),
        test_cmd,
        project_directory_content,
        APPLY_PATCH_TOOL_INSTRUCTIONS
    )
}

/// Build the user prompt for the AI agent
pub fn build_user_prompt(goal: &str, failure_context: &str) -> String {
    if failure_context.is_empty() {
        format!("Goal: {}", goal)
    } else {
        format!("Goal: {}\n\nPrevious iteration failed. Here are the details:\n{}\n\nIMPORTANT: There are very likely failures and errors in the output above. The best way to complete the task is to read the errors, understand the errors, and adjust the code to fix these errors as shown in the response.", goal, failure_context)
    }
}
