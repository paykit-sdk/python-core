"""
Utility functions for command processing

Provides helper functions for version normalization and provider string parsing
that are used across multiple commands.
"""

from typing import Tuple


def normalize_version(version: str) -> str:
    """
    Normalize version string to 3-digit format

    Converts version strings to standard X.Y.Z format by appending
    zeros as needed. "latest" is returned unchanged.

    Args:
        version: Version string (e.g., "1", "3.4", "2.1.5", "latest")

    Returns:
        Normalized version string (e.g., "1.0.0", "3.4.0", "2.1.5", "latest")

    Examples:
        >>> normalize_version("1")
        "1.0.0"
        >>> normalize_version("3.4")
        "3.4.0"
        >>> normalize_version("2.1.5")
        "2.1.5"
        >>> normalize_version("latest")
        "latest"
    """
    if version.lower() == "latest":
        return "latest"

    parts = version.split(".")

    # Pad with zeros to get 3 parts
    while len(parts) < 3:
        parts.append("0")

    # Take only first 3 parts
    parts = parts[:3]

    return ".".join(parts)


def parse_provider_string(provider_str: str) -> Tuple[str, str]:
    """
    Parse provider string into name and version

    Splits provider specification at '@' symbol and normalizes the version.
    If no version is specified, defaults to "latest".

    Args:
        provider_str: Provider string (e.g., "payme", "payme@1", "payme@3.4.0")

    Returns:
        Tuple of (provider_name, normalized_version)

    Examples:
        >>> parse_provider_string("payme")
        ("payme", "latest")
        >>> parse_provider_string("payme@1")
        ("payme", "1.0.0")
        >>> parse_provider_string("click@3.4")
        ("click", "3.4.0")
        >>> parse_provider_string("stripe@2.1.5")
        ("stripe", "2.1.5")
    """
    if "@" in provider_str:
        name, version = provider_str.split("@", 1)
        version = normalize_version(version)
    else:
        name = provider_str
        version = "latest"

    return name.strip(), version


def format_provider_list(providers: dict) -> str:
    """
    Format provider dictionary for display

    Args:
        providers: Dictionary mapping provider names to versions

    Returns:
        Formatted string listing providers
    """
    if not providers:
        return "No providers configured"

    lines = []
    for name, version in sorted(providers.items()):
        lines.append(f"  - {name} @ {version}")

    return "\n".join(lines)
