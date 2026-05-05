"""Styled questionary prompts. Everything user-facing goes through here."""

from __future__ import annotations

import questionary
from questionary import Style

ACTION_RENAME = "rename"
ACTION_UNDO = "undo"
ACTION_CANCEL = "cancel"

# Mid-tone palette: every color stays readable on both black and white
# terminals (no near-white text, no near-black text). The "question" and
# "text" classes deliberately have no foreground so the terminal's default
# foreground is used.
_PURPLE = "#7c3aed"
_ORANGE = "#ea580c"
_BLUE = "#2563eb"
_GREEN = "#15803d"
_RED = "#dc2626"
_GREY = "#64748b"

STYLE = Style(
    [
        ("qmark", f"fg:{_PURPLE} bold"),
        ("question", "bold"),
        ("answer", f"fg:{_ORANGE} bold"),
        ("pointer", f"fg:{_PURPLE} bold"),
        ("highlighted", f"fg:{_PURPLE} bold"),
        ("selected", f"fg:{_GREEN} bold"),
        ("separator", f"fg:{_GREY}"),
        ("instruction", f"fg:{_GREY} italic"),
        ("text", ""),
        ("disabled", f"fg:{_GREY} italic"),
    ]
)


def banner() -> None:
    questionary.print("picture-sort", style=f"fg:{_PURPLE} bold")
    questionary.print(
        "rename JPEGs by EXIF capture time — safe, idempotent, undoable",
        style=f"fg:{_BLUE}",
    )
    questionary.print("")


def ask_action() -> str | None:
    """Top-level menu. Returns one of the ACTION_* constants, or None."""
    return questionary.select(
        "What do you want to do?",
        choices=[
            questionary.Choice("Rename JPEGs in a folder", value=ACTION_RENAME),
            questionary.Choice("Undo a previous run", value=ACTION_UNDO),
            questionary.Choice("Cancel", value=ACTION_CANCEL),
        ],
        style=STYLE,
    ).ask()


def ask_path(message: str = "Folder with photos:") -> str | None:
    return questionary.path(
        message,
        only_directories=True,
        style=STYLE,
    ).ask()


def ask_recursive() -> bool:
    return bool(
        questionary.confirm(
            "Recurse into subfolders?",
            default=False,
            style=STYLE,
        ).ask()
    )


def ask_log_choice(labels: list[tuple[str, str]]) -> str | None:
    """Ask the user to pick a log file. `labels` is a list of (label, value)."""
    return questionary.select(
        "Which run do you want to undo?",
        choices=[questionary.Choice(label, value=value) for label, value in labels],
        style=STYLE,
    ).ask()


def info(text: str) -> None:
    questionary.print(text, style=f"fg:{_BLUE}")


def success(text: str) -> None:
    questionary.print(text, style=f"fg:{_GREEN} bold")


def warn(text: str) -> None:
    questionary.print(text, style=f"fg:{_ORANGE} bold")


def error(text: str) -> None:
    questionary.print(text, style=f"fg:{_RED} bold")
