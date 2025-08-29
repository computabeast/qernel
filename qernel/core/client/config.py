"""Configuration and exceptions for the Qernel client."""

import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

from typing import Optional, Any, Dict


class QernelAPIError(Exception):
    """Custom exception for Qernel API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        transcript: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        self.transcript = transcript
        super().__init__(self.message)


load_dotenv()


@dataclass
class QernelConfig:
    """Configuration class for Qernel client settings."""

    api_url: str = "https://d3nt1x9f8mnu77.cloudfront.net"
    api_key: Optional[str] = None
    timeout: int = 60
    # Slightly higher timeout for streaming SSE requests
    stream_timeout: int = 120
    max_retries: int = 3

    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("QERNEL_API_KEY")
        if not self.api_key:
            logging.warning(
                "No API key provided. Set QERNEL_API_KEY environment variable or pass api_key parameter."
            )

    def get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def validate(self) -> bool:
        if not self.api_key:
            raise QernelAPIError(
                "API key is required. Set QERNEL_API_KEY environment variable or pass api_key parameter."
            )
        return True
