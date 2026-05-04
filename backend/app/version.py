"""
Single-source version — reads from pyproject.toml via importlib.metadata.
"""
from importlib.metadata import version, PackageNotFoundError


def get_version() -> str:
    try:
        return version("spine-cli")
    except PackageNotFoundError:
        return "1.2.0"