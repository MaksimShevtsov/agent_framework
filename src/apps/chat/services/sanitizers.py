import base64
import os
import re
import html
from typing import Any, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import bleach
from bleach.sanitizer import ALLOWED_TAGS, ALLOWED_ATTRIBUTES
from validators import url


@dataclass
class SanitizationConfig:
    """Configuration for content sanitization"""

    max_text_length: int = 4096  # Maximum length for text content
    max_file_size: int = 10 * 1024 * 1024  # 10MB max file size
    allowed_file_types: Optional[set[str]] = None
    allowed_html_tags: Optional[set[str]] = None
    allowed_html_attributes: Optional[dict[str, list[str]]] = None

    def __post_init__(self):
        if self.allowed_file_types is None:
            self.allowed_file_types = {"text/plain", "audio/wav", "audio/mpeg"}

        if self.allowed_html_tags is None:
            self.allowed_html_tags = set(ALLOWED_TAGS)

        if self.allowed_html_attributes is None:
            self.allowed_html_attributes = ALLOWED_ATTRIBUTES


class InputSanitizer:
    def __init__(self, config: Optional[SanitizationConfig] = None):
        self.config = config or SanitizationConfig()

    def sanitize_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize the entire message"""
        try:
            if not isinstance(message_data, dict):
                raise ValueError("Message data must be a dictionary")

            # Sanitize message content
            content = message_data.get("content")
            if content:
                message_data["content"] = self.sanitize_text(content)

            return message_data

        except Exception as e:
            raise ValueError(f"Message sanitization failed: {str(e)}")

    def sanitize_text(self, text: str) -> str:
        """Sanitize text content"""
        if not isinstance(text, str):
            raise ValueError("Text content must be a string")

        # Trim whitespace
        text = text.strip()

        # Check length
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )

        # Remove null bytes
        text = text.replace("\x00", "")

        # HTML escape and sanitize
        text = html.escape(text)
        text = bleach.clean(
            text,
            tags=self.config.allowed_html_tags,
            attributes=self.config.allowed_html_attributes,
            strip=True,
        )

        return text

    def sanitize_file_data(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize file data"""
        if not isinstance(file_data, dict):
            raise ValueError("File data must be a dictionary")

        required_fields = {"name", "type", "size", "content"}
        if not all(field in file_data for field in required_fields):
            raise ValueError("Missing required file fields")

        # Sanitize file name
        file_name = self.sanitize_filename(file_data["name"])

        # Check file type
        file_type = str(file_data["type"]).lower()
        if file_type not in self.config.allowed_file_types:
            raise ValueError(f"File type not allowed: {file_type}")

        # Check file size
        file_size = int(file_data["size"])
        if file_size > self.config.max_file_size:
            raise ValueError(
                f"File size exceeds maximum of {self.config.max_file_size} bytes"
            )

        return {
            "name": file_name,
            "type": file_type,
            "size": file_size,
            "content": file_data["content"],  # Content should be base64 encoded
        }

    def sanitize_voice_data(self, voice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize voice data"""
        if not isinstance(voice_data, dict):
            raise ValueError("Voice data must be a dictionary")

        required_fields = {"duration", "format", "content"}
        if not all(field in voice_data for field in required_fields):
            raise ValueError("Missing required voice fields")

        # Validate duration
        duration = float(voice_data["duration"])
        if duration <= 0 or duration > 300:  # Max 5 minutes
            raise ValueError("Invalid voice duration")

        # Validate format
        allowed_formats = {"wav", "mp3", "ogg"}
        format_type = str(voice_data["format"]).lower()
        if format_type not in allowed_formats:
            raise ValueError(f"Voice format not allowed: {format_type}")

        return {
            "duration": duration,
            "format": format_type,
            "content": voice_data["content"],  # Content should be base64 encoded
        }

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize file name"""
        # Remove path components
        filename = os.path.basename(filename)

        # Remove null bytes and control characters
        filename = "".join(char for char in filename if ord(char) >= 32)

        # Replace potentially dangerous characters
        filename = re.sub(r'[\\/:*?"<>|]', "_", filename)

        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[: max_length - len(ext)] + ext

        return filename

    def sanitize_id(self, id_value: str) -> str:
        """Sanitize message ID"""
        # Allow only alphanumeric characters and specific separators
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", str(id_value))
        if len(sanitized) > 64:  # Limit length
            raise ValueError("Message ID too long")
        return sanitized

    def sanitize_timestamp(self, timestamp: str) -> str:
        """Sanitize timestamp"""
        try:
            # Parse and validate timestamp
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            # Return in consistent format
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            raise ValueError("Invalid timestamp format")

    def sanitize_url(self, url_string: str) -> str:
        """Sanitize URL"""
        if not url(url_string):
            raise ValueError("Invalid URL")
        return url_string

    def sanitize_base64(self, base64_string: str) -> str:
        """Validate base64 string"""
        try:
            # Remove data URL prefix if present
            if base64_string.startswith("data:"):
                base64_string = base64_string.split(",")[1]

            # Check if it's valid base64
            base64.b64decode(base64_string)
            return base64_string
        except Exception:
            raise ValueError("Invalid base64 data")
