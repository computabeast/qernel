"""Custom exceptions for the Qernel client."""

from typing import Optional


class QernelAPIError(Exception):
    """Custom exception for Qernel API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)
