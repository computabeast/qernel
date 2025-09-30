// Minimal adapter that reuses the user's provided implementation by `include!` from exe root when present.
// If not found, compile an internal copy (we embed a subset here to keep this crate self-contained).

// We expect the file to already be in this crate's directory per user's addition.
// If the user physically placed it at project root `src/exe/turn_diff_tracker.rs`, prefer that path via include!.

#[path = "../../turn_diff_tracker.rs"]
mod external;

pub use external::TurnDiffTracker;

