use anyhow::{Context, Result};
use serde_json::json;
use std::{path::PathBuf};
use std::fs;
use base64::{Engine as _, engine::general_purpose};

use crate::cmd::prototype::logging::debug_log;

#[derive(serde::Deserialize, Default, Debug)]
pub struct AiStep {
    pub action: String,
    #[allow(dead_code)] 
    pub rationale: Option<String>,
    #[allow(dead_code)] 
    pub patch: Option<String>,
    #[allow(dead_code)] 
    pub command: Option<String>,
}

/// Make OpenAI API request and parse response
pub fn make_openai_request(
    api_key: &str,
    model: &str,
    system_prompt: &str,
    user_prompt: &str,
    _tools: serde_json::Value,
    debug_file: &Option<PathBuf>,
) -> Result<AiStep> {
    make_openai_request_with_images(api_key, model, system_prompt, user_prompt, _tools, debug_file, None)
}

/// Make OpenAI API request with optional images
pub fn make_openai_request_with_images(
    api_key: &str,
    model: &str,
    system_prompt: &str,
    user_prompt: &str,
    _tools: serde_json::Value,
    debug_file: &Option<PathBuf>,
    images: Option<Vec<String>>,
) -> Result<AiStep> {
    // Calculate total context size for warning
    let total_context_size = system_prompt.len() + user_prompt.len();
    debug_log(debug_file, &format!("[ai] system prompt length: {} chars", system_prompt.len()), debug_file.is_some());
    debug_log(debug_file, &format!("[ai] user prompt length: {} chars", user_prompt.len()), debug_file.is_some());
    debug_log(debug_file, &format!("[ai] total context size: {} chars", total_context_size), debug_file.is_some());
    use reqwest::blocking::Client;
    use codex_core::tool_apply_patch::{
        create_apply_patch_freeform_tool,  // "custom" (free-form / grammar) — GPT-5 only
        create_apply_patch_json_tool,      // "function" (JSON schema)
    };
    
    // Validate API key
    if api_key.is_empty() {
        anyhow::bail!("OPENAI_API_KEY is empty");
    }
    if !api_key.starts_with("sk-") {
        anyhow::bail!("OPENAI_API_KEY doesn't look like a valid OpenAI API key (should start with 'sk-')");
    }
    debug_log(debug_file, &format!("[ai] Using API key: {}...", &api_key[..api_key.len().min(10)]), debug_file.is_some());

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(600)) // 10 minute timeout
        .build()
        .context("Failed to create HTTP client")?;

    // Select tools based on model
    let use_custom_tools = model.starts_with("gpt-5"); // e.g., "gpt-5-codex"
    
    let tools = if use_custom_tools {
        // GPT-5 models use custom freeform tools
        serde_json::to_value(vec![create_apply_patch_freeform_tool()]).expect("tools json")
    } else {
        // codex-mini-latest and other models use JSON function tools
        serde_json::to_value(vec![create_apply_patch_json_tool()]).expect("tools json")
    };
    
    debug_log(debug_file, &format!("[ai] tools json: {}",
        serde_json::to_string_pretty(&tools).unwrap_or_default()), debug_file.is_some());
    
    // Add retry logic for OpenAI API calls
    let mut attempts = 0;
    let max_attempts = 3;
    let resp = loop {
        attempts += 1;
        debug_log(debug_file, &format!("[ai] OpenAI API attempt {}/{}", attempts, max_attempts), debug_file.is_some());
        
        // Build the input array with optional images
        let mut input_array = vec![
            json!({"role": "system", "content": system_prompt}),
        ];
        
        // Add user content with optional images
        if let Some(image_paths) = &images {
            if !image_paths.is_empty() {
                debug_log(debug_file, &format!("[ai] attempting to encode {} images for request", image_paths.len()), debug_file.is_some());
                
                let mut user_content = vec![json!({"type": "input_text", "text": user_prompt})];
                let mut successful_images = 0;
                
                // Add each image to the content as base64 data URLs
                for image_path in image_paths {
                    match encode_image_to_base64(image_path) {
                        Ok(data_url) => {
                            user_content.push(json!({
                                "type": "input_image",
                                "image_url": data_url
                            }));
                            successful_images += 1;
                            debug_log(debug_file, &format!("[ai] successfully encoded image: {}", image_path), debug_file.is_some());
                        }
                        Err(e) => {
                            debug_log(debug_file, &format!("[ai] failed to encode image {}: {}", image_path, e), debug_file.is_some());
                            // Continue with other images even if one fails
                        }
                    }
                }
                
                debug_log(debug_file, &format!("[ai] successfully encoded {} out of {} images for model request", successful_images, image_paths.len()), debug_file.is_some());
                
                input_array.push(json!({
                    "role": "user",
                    "content": user_content
                }));
            } else {
                input_array.push(json!({"role": "user", "content": user_prompt}));
            }
        } else {
            input_array.push(json!({"role": "user", "content": user_prompt}));
        }
        
        let request = client
            .post("https://api.openai.com/v1/responses")
            .bearer_auth(api_key)
            .json(&json!({
                "model": model,
                "tools": tools,
                "tool_choice": "auto",
                "parallel_tool_calls": false,
                "input": input_array
            }));
        
        match request.send() {
            Ok(response) => break response,
            Err(e) => {
                if attempts >= max_attempts {
                    anyhow::bail!("OpenAI API failed after {} attempts: {}", max_attempts, e);
                }
                debug_log(debug_file, &format!("[ai] OpenAI API attempt {} failed: {}, retrying...", attempts, e), debug_file.is_some());
                std::thread::sleep(std::time::Duration::from_secs(2 * attempts as u64));
                continue;
            }
        }
    };
    
    let status = resp.status();
    debug_log(debug_file, &format!("[ai] openai status: {}", status), debug_file.is_some());
    
    // Check for API errors
    if !status.is_success() {
        let error_text = resp.text().unwrap_or_default();
        anyhow::bail!("OpenAI API error ({}): {}", status, error_text);
    }
    
    let raw = resp.text().context("openai response text")?;
    debug_log(debug_file, &format!("[ai] openai body length: {} chars", raw.len()), debug_file.is_some());
    
    // Debug: Print the raw response for troubleshooting
    debug_log(debug_file, &format!("[ai] openai raw response:\n{}", raw), false);
    
    // Parse response with better error handling
    let body: serde_json::Value = match serde_json::from_str(&raw) {
        Ok(parsed) => parsed,
        Err(e) => {
            debug_log(debug_file, &format!("[ai] Failed to parse JSON response: {}", e), debug_file.is_some());
            debug_log(debug_file, &format!("[ai] Raw response (first 500 chars): {}", &raw[..raw.len().min(500)]), debug_file.is_some());
            anyhow::bail!("Failed to parse OpenAI response JSON: {}", e);
        }
    };
    
    // Check for OpenAI API errors in the response body
    if let Some(error) = body.get("error") {
        if let Some(message) = error.get("message").and_then(|m| m.as_str()) {
            anyhow::bail!("OpenAI API error: {}", message);
        }
    }
    
    // Parse the response using the same logic as the original
    parse_ai_response(&body, debug_file)
}

fn parse_ai_response(body: &serde_json::Value, debug_file: &Option<PathBuf>) -> Result<AiStep> {
    // Prefer tool calls in the Responses API `output` array.
    if let Some(output) = body.get("output").and_then(|v| v.as_array()) {
        debug_log(debug_file, &format!("[ai] output array length: {}", output.len()), debug_file.is_some());
        for (i, item) in output.iter().enumerate() {
            debug_log(debug_file, &format!("[ai] output[{}]: {}", i, serde_json::to_string_pretty(item).unwrap_or_default()), debug_file.is_some());
        }
        
        // 1) Grammar-based custom tools (GPT-5 "custom_tool_call")
        if let Some(ctc) = output.iter().find(|item| {
            item.get("type").and_then(|v| v.as_str()) == Some("custom_tool_call")
                && item.get("name").and_then(|v| v.as_str()) == Some("apply_patch")
        }) {
            if let Some(input) = ctc.get("input").and_then(|v| v.as_str()) {
                debug_log(debug_file, &format!("[ai] custom_tool_call input (len={}):", input.len()), debug_file.is_some());
                if input.trim_start().starts_with("*** Begin Patch") {
                    return Ok(AiStep {
                        action: "apply_patch".to_string(),
                        rationale: None,
                        patch: Some(input.to_string()),
                        command: None,
                    });
                }
            }
        }
        
        // 2) JSON/function tools (handle both function_call and tool_call)
        if let Some(fc) = output.iter().find(|item| {
            let t = item.get("type").and_then(|v| v.as_str());
            t == Some("function_call") || t == Some("tool_call")
        }) {
            let name = fc.get("name").and_then(|v| v.as_str()).unwrap_or("");
            debug_log(debug_file, &format!("[ai] found function_call: {}", name), debug_file.is_some());
            
            if name == "apply_patch" {
                if let Some(args_str) = fc.get("arguments").and_then(|v| v.as_str()) {
                    debug_log(debug_file, &format!("[ai] function_call apply_patch args:\\n{}", args_str), debug_file.is_some());
                    let args_json: serde_json::Value =
                        serde_json::from_str(args_str).unwrap_or_else(|_| json!({}));
                    if let Some(input) = args_json.get("input").and_then(|v| v.as_str()) {
                        if input.trim_start().starts_with("*** Begin Patch") {
                            return Ok(AiStep {
                                action: "apply_patch".to_string(),
                                rationale: None,
                                patch: Some(input.to_string()),
                                command: None,
                            });
                        }
                    }
                }
            } else if name == "shell" {
                if let Some(args_str) = fc.get("arguments").and_then(|v| v.as_str()) {
                    debug_log(debug_file, &format!("[ai] function_call shell args:\\n{}", args_str), debug_file.is_some());
                    let args_json: serde_json::Value =
                        serde_json::from_str(args_str).unwrap_or_else(|_| json!({}));
                    if let Some(command) = args_json.get("command").and_then(|v| v.as_str()) {
                        return Ok(AiStep {
                            action: "shell".to_string(),
                            rationale: None,
                            patch: None,
                            command: Some(command.to_string()),
                        });
                    }
                }
            }
        }
    }

    // Fallback: parse content as our JSON action schema
    if let Some(output) = body["output"].as_array() {
        debug_log(debug_file, "[ai] trying fallback JSON parsing...", debug_file.is_some());
        if let Some(message) = output.iter().find(|item| item["type"].as_str() == Some("message")) {
            debug_log(debug_file, "[ai] found message in output", debug_file.is_some());
            if let Some(content_array) = message["content"].as_array() {
                debug_log(debug_file, &format!("[ai] content array length: {}", content_array.len()), debug_file.is_some());
                if let Some(text_content) = content_array.iter().find(|c| c["type"].as_str() == Some("output_text")) {
                    if let Some(content) = text_content["text"].as_str() {
                        debug_log(debug_file, &format!("[ai] openai content (to-parse):\n{}", content), debug_file.is_some());
                        let step: AiStep = serde_json::from_str(content).context("parse ai json")?;
                        debug_log(debug_file, &format!("[ai] parsed step: {:?}", step), debug_file.is_some());
                        return Ok(step);
                    }
                }
            }
        }
    }

    // Final fallbacks: try output_text (SDK convenience), then message content.
    debug_log(debug_file, "[ai] trying final fallbacks...", debug_file.is_some());
    if let Some(s) = body.get("output_text").and_then(|v| v.as_str()) {
        debug_log(debug_file, &format!("[ai] found output_text: {}", s), debug_file.is_some());
        if let Ok(step) = serde_json::from_str::<AiStep>(s) {
            debug_log(debug_file, &format!("[ai] parsed step from output_text: {:?}", step), debug_file.is_some());
            return Ok(step);
        } else {
            debug_log(debug_file, "[ai] failed to parse output_text as AiStep", debug_file.is_some());
        }
    }
    
    if let Some(output) = body.get("output").and_then(|v| v.as_array()) {
        for item in output {
            if item.get("type").and_then(|v| v.as_str()) == Some("message") {
                if let Some(s) = item.get("content").and_then(|v| v.as_str()) {
                    if let Ok(step) = serde_json::from_str::<AiStep>(s) {
                        debug_log(debug_file, "[ai] parsed step from message.content (string)", debug_file.is_some());
                        return Ok(step);
                    }
                } else if let Some(parts) = item.get("content").and_then(|v| v.as_array()) {
                    let text = parts
                        .iter()
                        .filter_map(|p| p.get("text").and_then(|t| t.as_str()))
                        .collect::<String>();
                    if let Ok(step) = serde_json::from_str::<AiStep>(&text) {
                        debug_log(debug_file, "[ai] parsed step from message.content parts", debug_file.is_some());
                        return Ok(step);
                    }
                }
            }
        }
    }
    
    let kinds = body
        .get("output")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .map(|i| i.get("type").and_then(|v| v.as_str()).unwrap_or("?").to_string())
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    
    // Check if we have reasoning types but also function calls
    let has_reasoning = kinds.contains(&"reasoning".to_string());
    let has_function_call = kinds.contains(&"function_call".to_string()) || kinds.contains(&"tool_call".to_string());
    
    // If we have reasoning but no function calls, the model might be stuck
    if has_reasoning && !has_function_call {
        anyhow::bail!("Model is reasoning but not taking action. Output types = {:?}. This might indicate the model needs clearer instructions or the task is too complex, or an alternative error has occured.", kinds)
    }
    
    anyhow::bail!("No actionable tool call or parseable text in response; output types = {:?}", kinds)
}

/// Encode an image file to base64 data URL
fn encode_image_to_base64(image_path: &str) -> Result<String> {
    // Read the image file
    let image_data = fs::read(image_path)
        .context("Failed to read image file")?;
    
    // Encode to base64
    let base64_string = general_purpose::STANDARD.encode(&image_data);
    
    // Determine MIME type based on file extension
    let mime_type = get_image_mime_type(image_path);
    
    // Create data URL
    Ok(format!("data:{};base64,{}", mime_type, base64_string))
}

/// Get MIME type based on file extension
fn get_image_mime_type(image_path: &str) -> &'static str {
    if let Some(extension) = std::path::Path::new(image_path)
        .extension()
        .and_then(|ext| ext.to_str())
    {
        match extension.to_lowercase().as_str() {
            "jpg" | "jpeg" => "image/jpeg",
            "png" => "image/png",
            "gif" => "image/gif",
            "bmp" => "image/bmp",
            "webp" => "image/webp",
            _ => "image/jpeg", // Default fallback
        }
    } else {
        "image/jpeg" // Default fallback
    }
}
