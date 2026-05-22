import json
import re
from typing import Any

PATTERNS = [
    # GitHub tokens
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),

    # OpenAI-style keys
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),

    # JWT-like tokens
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),

    # Generic key-value secrets
    re.compile(
        r"(?i)\b(password|authorization|api[_-]?key|token|secret|access[_-]?key)\b\s*[:=]\s*[^\s,;]+"
    ),

    # Bearer tokens
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{20,}"),
]


def redact(value: Any) -> Any:
    """
    Recursively redact secrets from strings, dicts, and lists.
    """
    if isinstance(value, str):
        redacted = value
        for pattern in PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}

    if isinstance(value, list):
        return [redact(item) for item in value]

    return value


def redact_for_log(value: Any) -> str:
    """
    Convert any value to a redacted string suitable for logging.
    """
    redacted = redact(value)

    if isinstance(redacted, (dict, list)):
        return json.dumps(redacted, ensure_ascii=False)

    return str(redacted)