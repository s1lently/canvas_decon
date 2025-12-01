"""Security utilities for Canvas LMS Automation

Provides:
- Path sanitization (prevent traversal attacks)
- API key validation
- Safe filename generation
"""
import os
import re
from typing import Optional
from .exceptions import ConfigError


# Windows reserved names
_WINDOWS_RESERVED = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
})

# Dangerous characters for filenames
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_path(name: str, max_length: int = 200, allow_spaces: bool = True) -> str:
    """Safely sanitize folder/file names to prevent path traversal

    Args:
        name: Raw name to sanitize
        max_length: Maximum allowed length (default 200)
        allow_spaces: Whether to preserve spaces (default True)

    Returns:
        Safe filename string

    Examples:
        >>> sanitize_path("../../../etc/passwd")
        'etc_passwd'
        >>> sanitize_path("Week 5: Quiz #1")
        'Week 5_ Quiz _1'
        >>> sanitize_path("CON")
        '_CON'
    """
    if not name:
        return "unnamed"

    # Step 1: Remove/replace dangerous chars
    name = _INVALID_CHARS.sub('_', name)

    # Step 2: Remove path traversal patterns
    # Handle ../, ..\, multiple dots
    while '..' in name:
        name = name.replace('..', '_')

    # Remove leading/trailing dots and spaces
    name = name.strip('. \t\n\r')

    # Step 3: Remove leading slashes (absolute path prevention)
    name = name.lstrip('/\\')

    # Step 4: Handle spaces if needed
    if not allow_spaces:
        name = name.replace(' ', '_')

    # Step 5: Collapse multiple underscores
    name = re.sub(r'_+', '_', name)

    # Step 6: Windows reserved names
    if name.upper() in _WINDOWS_RESERVED:
        name = f"_{name}"

    # Step 7: Length limit
    if len(name) > max_length:
        name = name[:max_length].rstrip('_. ')

    # Step 8: Final validation
    if not name or name in ('.', '..'):
        return "unnamed"

    return name


def validate_api_key(key: Optional[str], provider: str) -> str:
    """Validate API key format and presence

    Args:
        key: API key to validate
        provider: Provider name ('gemini' or 'claude')

    Returns:
        The validated key

    Raises:
        ConfigError: If key is missing or invalid format
    """
    if not key:
        raise ConfigError(
            f"{provider.upper()}_API_KEY not configured. "
            f"Set in account_config.json or {provider.upper()}_API_KEY env var."
        )

    key = key.strip()

    # Basic format validation
    if provider.lower() == 'gemini':
        if not key.startswith('AIza'):
            raise ConfigError(f"Invalid Gemini API key format (should start with 'AIza')")
    elif provider.lower() == 'claude':
        if not key.startswith('sk-ant-'):
            raise ConfigError(f"Invalid Claude API key format (should start with 'sk-ant-')")

    return key


def safe_join(base: str, *paths: str) -> str:
    """Safely join paths, preventing traversal outside base

    Args:
        base: Base directory (must be absolute)
        *paths: Path components to join

    Returns:
        Joined path guaranteed to be under base

    Raises:
        ValueError: If result would escape base directory
    """
    base = os.path.abspath(base)
    result = base

    for p in paths:
        # Sanitize each component
        safe_p = sanitize_path(p)
        result = os.path.normpath(os.path.join(result, safe_p))

        # Verify still under base
        if not result.startswith(base):
            raise ValueError(f"Path traversal detected: {p}")

    return result
