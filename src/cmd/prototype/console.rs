use std::io::{self, Write, stdin};
use std::io::IsTerminal;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use anyhow::Result;
use syntect::{
    easy::HighlightLines,
    highlighting::{Style, ThemeSet, Theme},
    parsing::SyntaxSet,
    util::as_24_bit_terminal_escaped,
};

// ANSI color codes
const RESET: &str = "\x1b[0m";
const DIM: &str = "\x1b[2m";          // SGR 2: faint/decreased intensity (may be unsupported on some TTYs)
const GRAY: &str = "\x1b[90m";        // bright black (reliable gray fallback)
const GREEN: &str = "\x1b[32m";
const RED: &str = "\x1b[31m";
const YELLOW: &str = "\x1b[33m";
const BLUE: &str = "\x1b[34m";
const CYAN: &str = "\x1b[36m";
const BOLD: &str = "\x1b[1m";

/// A native Rust console streamer that provides real-time output with better formatting
pub struct ConsoleStreamer {
    output: Arc<Mutex<io::Stdout>>,
    syntax_set: SyntaxSet,
    grayscale_theme: Theme,
    color_enabled: bool,
    faint_seq: &'static str,
    reasoning_open: Arc<Mutex<bool>>,
}

impl ConsoleStreamer {
    pub fn new() -> Self {
        let syntax_set = SyntaxSet::load_defaults_newlines();
        let grayscale_theme = Self::create_grayscale_theme();
        // Determine whether to emit ANSI styles
        let color_enabled = io::stdout().is_terminal() && std::env::var_os("NO_COLOR").is_none();

        // On Windows, enable VT processing so ANSI escape sequences render.
        #[cfg(windows)]
        if color_enabled {
            let _ = Self::enable_vt_mode();
        }

        // Prefer SGR 2 (dim). Some terminals ignore it; we'll still send it,
        // but we also keep a GRAY fallback if you'd rather force a color.
        let faint_seq = DIM;

        Self {
            output: Arc::new(Mutex::new(io::stdout())),
            syntax_set,
            grayscale_theme,
            color_enabled,
            faint_seq,
            reasoning_open: Arc::new(Mutex::new(false)),
        }
    }

    #[cfg(windows)]
    fn enable_vt_mode() -> Result<()> {
        use windows_sys::Win32::Foundation::INVALID_HANDLE_VALUE;
        use windows_sys::Win32::System::Console::{
            GetConsoleMode, SetConsoleMode, GetStdHandle,
            ENABLE_VIRTUAL_TERMINAL_PROCESSING, STD_OUTPUT_HANDLE
        };
        unsafe {
            let h = GetStdHandle(STD_OUTPUT_HANDLE);
            if h == INVALID_HANDLE_VALUE { return Ok(()); }
            let mut mode = 0;
            if GetConsoleMode(h, &mut mode) == 0 { return Ok(()); }
            let _ = SetConsoleMode(h, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
        }
        Ok(())
    }

    /// Create a custom grayscale theme for syntax highlighting
    fn create_grayscale_theme() -> Theme {
        use syntect::highlighting::Color;
        
        // Use a simpler approach - load a default theme and modify it
        let theme_set = ThemeSet::load_defaults();
        let mut theme = theme_set.themes.get("base16-ocean.dark")
            .or_else(|| theme_set.themes.values().next())
            .unwrap()
            .clone();
        
        // Modify the theme to be grayscale
        theme.settings.background = Some(Color { r: 0, g: 0, b: 0, a: 255 });
        theme.settings.foreground = Some(Color { r: 200, g: 200, b: 200, a: 255 });
        theme.settings.selection = Some(Color { r: 100, g: 100, b: 100, a: 255 });
        theme.settings.line_highlight = Some(Color { r: 20, g: 20, b: 20, a: 255 });
        
        theme
    }

    /// Detect file type from file path
    fn detect_file_type(&self, file_path: &str) -> &str {
        if let Some(ext) = std::path::Path::new(file_path).extension() {
            match ext.to_str().unwrap_or("").to_lowercase().as_str() {
                "rs" => "Rust",
                "py" => "Python", 
                "js" => "JavaScript",
                "ts" => "TypeScript",
                "java" => "Java",
                "cpp" | "cc" | "cxx" => "C++",
                "c" => "C",
                "go" => "Go",
                "php" => "PHP",
                "rb" => "Ruby",
                "swift" => "Swift",
                "kt" => "Kotlin",
                "scala" => "Scala",
                "sh" => "Bash",
                "html" => "HTML",
                "css" => "CSS",
                "json" => "JSON",
                "yaml" | "yml" => "YAML",
                "xml" => "XML",
                "md" => "Markdown",
                "sql" => "SQL",
                "dockerfile" => "Dockerfile",
                _ => "Text",
            }
        } else {
            "Text"
        }
    }

    /// Print a message with proper formatting and immediate flush
    pub fn print(&self, message: &str) -> Result<()> {
        let mut output = self.output.lock().unwrap();
        write!(output, "{}", message)?;
        output.flush()?;
        Ok(())
    }

    /// Print a message with newline and flush
    pub fn println(&self, message: &str) -> Result<()> {
        let mut output = self.output.lock().unwrap();
        writeln!(output, "{}", message)?;
        output.flush()?;
        Ok(())
    }

    /// Begin a live "reasoning" section. Optional, but nice for headings.
    pub fn reasoning_begin(&self) -> Result<()> {
        let mut open = self.reasoning_open.lock().unwrap();
        if !*open {
            let mut out = self.output.lock().unwrap();
            if self.color_enabled {
                write!(out, "{}[REASONING]{} ", self.faint_seq, RESET)?;
            } else {
                write!(out, "[REASONING] ")?;
            }
            out.flush()?;
            *open = true;
        }
        Ok(())
    }

    /// Print a streamed reasoning delta in faint text.
    pub fn reasoning_delta(&self, delta: &str) -> Result<()> {
        let mut out = self.output.lock().unwrap();
        if self.color_enabled {
            // Write each chunk faint, then reset to avoid leaking style.
            write!(out, "{}{}{}", self.faint_seq, delta, RESET)?;
        } else {
            write!(out, "{}", delta)?;
        }
        out.flush()?;
        Ok(())
    }

    /// End the reasoning block (adds a newline and closes the section).
    pub fn reasoning_end(&self) -> Result<()> {
        let mut open = self.reasoning_open.lock().unwrap();
        if *open {
            let mut out = self.output.lock().unwrap();
            writeln!(out)?;
            out.flush()?;
            *open = false;
        }
        Ok(())
    }

    /// Print a section header with visual separators
    pub fn section(&self, title: &str) -> Result<()> {
        self.println(&format!("\n{}[{}]{}", BOLD, title, RESET))?;
        Ok(())
    }


    /// Print success message with green indicator
    pub fn success(&self, message: &str) -> Result<()> {
        self.println(&format!("{}[SUCCESS]{} {}", GREEN, RESET, message))?;
        Ok(())
    }

    /// Print error message with red indicator
    pub fn error(&self, message: &str) -> Result<()> {
        self.println(&format!("{}[ERROR]{} {}", RED, RESET, message))?;
        Ok(())
    }

    /// Print warning message with yellow indicator
    pub fn warning(&self, message: &str) -> Result<()> {
        self.println(&format!("{}[WARNING]{} {}", YELLOW, RESET, message))?;
        Ok(())
    }

    /// Print info message with blue indicator
    pub fn info(&self, message: &str) -> Result<()> {
        self.println(&format!("{}[INFO]{} {}", BLUE, RESET, message))?;
        Ok(())
    }

    /// Show context size warning for large prompts
    pub fn context_size_warning(&self, context_size: usize) -> Result<()> {
        const LARGE_CONTEXT_THRESHOLD: usize = 50_000; // 50k characters
        
        if context_size > LARGE_CONTEXT_THRESHOLD {
            let size_kb = context_size / 1024;
            self.println("")?;
            self.warning(&format!("Large context detected: {} characters ({} KB)", context_size, size_kb))?;
            self.warning("This might take longer than expected to process...")?;
            self.println("")?;
        }
        Ok(())
    }


    /// Start an animated spinner for long-running operations
    pub fn start_spinner(&self, message: &str) -> Arc<Mutex<bool>> {
        let running = Arc::new(Mutex::new(true));
        let running_clone = Arc::clone(&running);
        let output_clone = Arc::clone(&self.output);
        let message = message.to_string();
        
        thread::spawn(move || {
            let spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
            let mut i = 0;
            
            while *running_clone.lock().unwrap() {
                let mut output = output_clone.lock().unwrap();
                write!(output, "\r{}[THINKING]{} {} {}", CYAN, RESET, message, spinner_chars[i]).unwrap();
                output.flush().unwrap();
                drop(output);
                thread::sleep(Duration::from_millis(100));
                i = (i + 1) % spinner_chars.len();
            }
            
            // Clear the spinner line
            let mut output = output_clone.lock().unwrap();
            write!(output, "\r{}", " ".repeat(80)).unwrap();
            write!(output, "\r").unwrap();
            output.flush().unwrap();
        });
        
        running
    }

    /// Start an animated spinner with timer for long-running operations
    pub fn start_spinner_with_timer(&self, message: &str, total_timeout_secs: u64) -> Arc<Mutex<bool>> {
        let running = Arc::new(Mutex::new(true));
        let running_clone = Arc::clone(&running);
        let output_clone = Arc::clone(&self.output);
        let message = message.to_string();
        let start_time = std::time::Instant::now();
        
        thread::spawn(move || {
            let spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
            let mut i = 0;
            let mut timer_started = false;
            
            while *running_clone.lock().unwrap() {
                let elapsed = start_time.elapsed();
                let elapsed_secs = elapsed.as_secs();
                let remaining_secs = total_timeout_secs.saturating_sub(elapsed_secs);
                
                let mut output = output_clone.lock().unwrap();
                
                // Start showing timer after 1 minute
                if elapsed_secs >= 60 && !timer_started {
                    timer_started = true;
                    write!(output, "\n{}[INFO]{} Timer started - showing remaining time\n", BLUE, RESET).unwrap();
                }
                
                if timer_started {
                    let minutes = remaining_secs / 60;
                    let seconds = remaining_secs % 60;
                    write!(output, "\r{}[THINKING]{} {} {} {}[TIMER]{} {}m {}s remaining", 
                           CYAN, RESET, message, spinner_chars[i], YELLOW, RESET, minutes, seconds).unwrap();
                } else {
                    write!(output, "\r{}[THINKING]{} {} {}", CYAN, RESET, message, spinner_chars[i]).unwrap();
                }
                
                output.flush().unwrap();
                drop(output);
                thread::sleep(Duration::from_millis(100));
                i = (i + 1) % spinner_chars.len();
            }
            
            // Clear the spinner line
            let mut output = output_clone.lock().unwrap();
            write!(output, "\r{}", " ".repeat(100)).unwrap();
            write!(output, "\r").unwrap();
            output.flush().unwrap();
        });
        
        running
    }

    /// Stop the spinner
    pub fn stop_spinner(&self, running: &Arc<Mutex<bool>>) {
        *running.lock().unwrap() = false;
        thread::sleep(Duration::from_millis(150));
    }

    /// Print failure message
    pub fn failure_completion(&self, reason: &str) -> Result<()> {
        self.println("")?;
        self.error(&format!("Implementation failed: {}", reason))?;
        Ok(())
    }

    /// Typewriter effect for text
    pub fn typewriter(&self, text: &str, delay_ms: u64) -> Result<()> {
        for ch in text.chars() {
            self.print(&ch.to_string())?;
            thread::sleep(Duration::from_millis(delay_ms));
        }
        self.println("")?;
        Ok(())
    }

    /// Fade-in effect for text with progressive reveal
    pub fn fade_in(&self, text: &str, steps: u32) -> Result<()> {
        let chars: Vec<char> = text.chars().collect();
        let step_size = chars.len() as f32 / steps as f32;
        
        for i in 0..=steps {
            let end_idx = ((i as f32 * step_size) as usize).min(chars.len());
            let visible_text: String = chars[..end_idx].iter().collect();
            
            self.print(&format!("\r{}", visible_text))?;
            thread::sleep(Duration::from_millis(50));
        }
        self.println("")?;
        Ok(())
    }


    /// Show syntax-highlighted code in a nice format
    pub fn show_code(&self, code: &str, language: &str, title: Option<&str>) -> Result<()> {
        if let Some(title) = title {
            self.section(title)?;
        }
        
        self.println(&format!("{}[CODE]{} {}", CYAN, RESET, language))?;
        self.println("")?;
        
        // Show syntax-highlighted code
        self.highlight_code(code, language)?;
        
        self.println("")?;
        Ok(())
    }

    /// Enhanced patch preview with grayscale syntax highlighting
    pub fn patch_preview(&self, patch: &str) -> Result<()> {
        self.section("Code Changes")?;
        
        // Parse the patch to extract file changes
        let mut in_changes = false;
        let mut current_file = String::new();
        let mut changes = Vec::new();
        
        for line in patch.lines() {
            if line.starts_with("*** Begin Patch") {
                in_changes = true;
                continue;
            }
            if line.starts_with("*** End Patch") {
                break;
            }
            if in_changes {
                if line.starts_with("diff --git") {
                    // Extract filename from diff header
                    if let Some(start) = line.find("b/") {
                        if let Some(end) = line[start + 2..].find(' ') {
                            current_file = line[start + 2..start + 2 + end].to_string();
                        }
                    }
                } else if line.starts_with("+++") {
                    // Extract filename from +++ line
                    if let Some(start) = line.find("b/") {
                        current_file = line[start + 2..].to_string();
                    }
                } else if line.starts_with("+") || line.starts_with("-") || line.starts_with(" ") {
                    changes.push((current_file.clone(), line.to_string()));
                }
            }
        }
        
        if changes.is_empty() {
            self.warning("No changes detected in patch")?;
            return Ok(());
        }
        
        // Show a clean summary of changes
        self.println(&format!("{}[CHANGES]{} The AI is making these changes:", CYAN, RESET))?;
        self.println("")?;
        
        // Group changes by file
        let mut file_changes: std::collections::HashMap<String, Vec<String>> = std::collections::HashMap::new();
        for (file, line) in changes {
            file_changes.entry(file).or_insert_with(Vec::new).push(line);
        }
        
        // Process each file with syntax highlighting
        for (file, file_lines) in file_changes {
            if !file.is_empty() {
                self.println(&format!("{}File: {}:{}", BLUE, file, RESET))?;
            }
            
            // Show the diff with syntax highlighting
            self.highlight_diff(&file_lines, &file)?;
            
            self.println("")?;
        }
        
        Ok(())
    }

    /// Highlight code with grayscale syntax highlighting
    pub fn highlight_code(&self, code: &str, language: &str) -> Result<()> {
        // Detect syntax
        let syntax = self.syntax_set.find_syntax_by_name(language)
            .or_else(|| self.syntax_set.find_syntax_by_extension(language))
            .unwrap_or_else(|| self.syntax_set.find_syntax_plain_text());
        
        // Create highlighter with grayscale theme
        let mut highlighter = HighlightLines::new(syntax, &self.grayscale_theme);
        
        // Process each line with syntax highlighting
        for line in code.lines() {
            let ranges: Vec<(Style, &str)> = highlighter.highlight_line(line, &self.syntax_set)?;
            let highlighted_content = as_24_bit_terminal_escaped(&ranges[..], false);
            self.println(&highlighted_content)?;
        }
        
        Ok(())
    }

    /// Highlight code block with language detection
    pub fn highlight_code_block(&self, code: &str, file_path: &str) -> Result<()> {
        let file_type = self.detect_file_type(file_path);
        self.highlight_code(code, file_type)
    }

    /// Highlight diff with syntax highlighting using grayscale theme
    fn highlight_diff(&self, file_lines: &[String], file_path: &str) -> Result<()> {
        // Detect syntax
        let file_type = self.detect_file_type(file_path);
        let syntax = self.syntax_set.find_syntax_by_name(file_type)
            .or_else(|| self.syntax_set.find_syntax_by_extension(
                std::path::Path::new(file_path)
                    .extension()
                    .and_then(|ext| ext.to_str())
                    .unwrap_or("")
            ))
            .unwrap_or_else(|| self.syntax_set.find_syntax_plain_text());
        
        // Create highlighter with grayscale theme
        let mut highlighter = HighlightLines::new(syntax, &self.grayscale_theme);
        
        // Process each line with diff markers and syntax highlighting
        for line in file_lines {
            let (marker, content) = if line.starts_with("+") {
                (format!("  {}[+]{} ", GREEN, RESET), &line[1..])
            } else if line.starts_with("-") {
                (format!("  {}[-]{} ", RED, RESET), &line[1..])
            } else {
                (format!("    "), line.as_str())
            };
            
            // Apply syntax highlighting to the content
            if !content.trim().is_empty() {
                let ranges: Vec<(Style, &str)> = highlighter.highlight_line(content, &self.syntax_set)?;
                let highlighted_content = as_24_bit_terminal_escaped(&ranges[..], false);
                self.println(&format!("{}{}", marker, highlighted_content))?;
            } else {
                self.println(&format!("{}{}", marker, content))?;
            }
        }
        
        Ok(())
    }

    /// Ask user for confirmation before continuing
    pub fn ask_continue(&self, message: &str) -> Result<bool> {
        self.println("")?;
        self.section("User Confirmation Required")?;
        self.typewriter(&format!("{}", message), 10)?;
        self.typewriter("Press Enter to continue, or 'q' to quit: ", 5)?;
        
        let mut input = String::new();
        stdin().read_line(&mut input)?;
        
        let response = input.trim().to_lowercase();
        Ok(response != "q" && response != "quit" && response != "exit")
    }

    /// Enhanced iteration header with animation
    pub fn animated_iteration_header(&self, iteration: u32, max_iterations: u32) -> Result<()> {
        self.println("")?;
        
        // Animated header
        let header = format!("{}[AI AGENT]{} Iteration {}/{}", BOLD, RESET, iteration, max_iterations);
        self.fade_in(&header, 20)?;
        
        Ok(())
    }




    /// Enhanced success completion with celebration
    pub fn animated_success_completion(&self) -> Result<()> {
        self.println("")?;
        self.success("Implementation complete!")?;
        Ok(())
    }

    /// Debug-only execution result (only shown in debug mode)
    pub fn debug_execution_result(&self, command: &str, exit_code: i32, stdout: &str, stderr: &str) -> Result<()> {
        self.section("Debug Execution Result")?;
        
        let status = if exit_code == 0 { 
            format!("{}[SUCCESS]{} Succeeded", GREEN, RESET) 
        } else { 
            format!("{}[FAILED]{} Failed", RED, RESET) 
        };
        
        self.typewriter(&format!("{}[COMMAND]{} {}", CYAN, RESET, command), 5)?;
        self.typewriter(&format!("{}[STATUS]{} {} (exit code: {})", BLUE, RESET, status, exit_code), 5)?;
        
        if !stdout.is_empty() {
            self.println(&format!("{}[OUTPUT]{}", YELLOW, RESET))?;
            for line in stdout.lines() {
                self.println(&format!("  {}", line))?;
            }
        }
        
        if !stderr.is_empty() {
            self.println(&format!("{}[ERRORS]{}", RED, RESET))?;
            for line in stderr.lines() {
                self.println(&format!("  {}", line))?;
            }
        }
        
        self.println("")?;
        Ok(())
    }
}

impl Default for ConsoleStreamer {
    fn default() -> Self {
        Self::new()
    }
}
