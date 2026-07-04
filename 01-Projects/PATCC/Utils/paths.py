"""
PATCC Path Utilities

Shared path helper functions used throughout the project.
"""

from pathlib import Path


def project_root() -> Path:
    """Return the AI-Trading project root."""
    return Path(__file__).resolve().parents[3]


def patcc_root() -> Path:
    """Return the PATCC root directory."""
    return project_root() / "01-Projects" / "PATCC"


def config_dir() -> Path:
    return patcc_root() / "Config"


def core_dir() -> Path:
    return patcc_root() / "Core"


def data_dir() -> Path:
    return patcc_root() / "Data"


def reports_dir() -> Path:
    return patcc_root() / "Reports"


def logs_dir() -> Path:
    return patcc_root() / "Logs"


def tests_dir() -> Path:
    return patcc_root() / "Tests"
