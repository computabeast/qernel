//! Minimal core exposing patching, exec, and turn diff tracking.

#![deny(clippy::print_stdout, clippy::print_stderr)]

pub mod bash;
pub mod exec;
pub mod parse_command;
pub mod shell;
pub mod spawn;
pub mod turn_diff_tracker;

// Local minimal protocol for internal types used by turn_diff_tracker
pub mod protocol;

// Expose unified exec session manager API for tests/integration
pub mod unified_exec;

// Minimal subset of upstream openai_tools contracts to support apply_patch tool calls
pub mod openai_tools {
    use serde::Serialize;
    use std::collections::BTreeMap;

    #[derive(Debug, Serialize)]
    #[serde(rename_all = "snake_case")]
    pub enum OpenAiToolType { Function, Freeform }

    #[derive(Debug, Serialize)]
    pub struct ResponsesApiTool {
        pub name: String,
        pub description: String,
        pub strict: bool,
        pub parameters: JsonSchema,
    }

    #[derive(Debug, Serialize)]
    pub struct FreeformToolFormat { pub r#type: String, pub syntax: String, pub definition: String }

    #[derive(Debug, Serialize)]
    pub struct FreeformTool { pub name: String, pub description: String, pub format: FreeformToolFormat }

    #[derive(Debug, Serialize)]
    #[serde(tag = "type")]
    pub enum OpenAiTool { 
        #[serde(rename = "function")]
        Function(ResponsesApiTool), 
        #[serde(rename = "custom")]
        Freeform(FreeformTool) 
    }

    #[derive(Debug, Serialize)]
    #[serde(untagged)]
    pub enum JsonSchema {
        Object { 
            r#type: String,
            properties: BTreeMap<String, JsonSchema>, 
            required: Option<Vec<String>>, 
            additional_properties: Option<bool> 
        },
        String { 
            r#type: String,
            description: Option<String> 
        },
    }
}

pub mod tool_apply_patch;
