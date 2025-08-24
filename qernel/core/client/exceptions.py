"""Custom exceptions for the Qernel client."""

from typing import Optional, Any, Dict, List


class QernelAPIError(Exception):
    """Custom exception for Qernel API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None, transcript: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        # Optional structured transcript (JSON-serializable) for debugging/replay
        self.transcript = transcript
        super().__init__(self.message)
