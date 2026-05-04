"""
Theme constants for SpineDoc Interaction presentation.
"""

from enum import Enum

class ConfidenceColor(Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    BLUE = "BLUE"

COLOR_ICONS = {
    ConfidenceColor.GREEN: "🟢",
    ConfidenceColor.YELLOW: "🟡",
    ConfidenceColor.RED: "🔴",
    ConfidenceColor.BLUE: "🔵",
}

COLOR_STYLES = {
    "GREEN": "green",
    "YELLOW": "yellow",
    "RED": "red",
    "BLUE": "blue",
}

PANEL_BORDER_STYLES = {
    "GREEN": "green",
    "YELLOW": "cyan",
    "RED": "red",
    "BLUE": "blue",
}

FEISHU_THEME = {
    "GREEN": "green",
    "YELLOW": "blue",
    "RED": "red",
    "BLUE": "default",
}
