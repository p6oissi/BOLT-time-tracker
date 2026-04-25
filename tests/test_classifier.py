"""Tests for heuristic task classification."""

import pytest

from tracker.classifier import classify


@pytest.mark.parametrize(
    "process_name, window_title, expected",
    [
        # coding
        ("pycharm64.exe", "main.py - MyProject", "coding"),
        ("Code.exe", "index.ts - my-app", "coding"),
        ("idea64.exe", "build.gradle - Backend", "coding"),
        # version control
        ("sourcetree.exe", "MyRepo - SourceTree", "version_control"),
        ("git.exe", "git commit", "version_control"),
        # terminal
        ("cmd.exe", "C:\\Windows\\System32", "terminal"),
        ("WindowsTerminal.exe", "PowerShell", "terminal"),
        ("powershell.exe", "Administrator: Windows PowerShell", "terminal"),
        # browsing
        ("chrome.exe", "Stack Overflow - Google Chrome", "browsing"),
        ("msedge.exe", "GitHub - Microsoft Edge", "browsing"),
        ("firefox.exe", "MDN Web Docs — Firefox", "browsing"),
        # communication
        ("Teams.exe", "Microsoft Teams", "communication"),
        ("slack.exe", "#general - Slack", "communication"),
        ("discord.exe", "Discord", "communication"),
        # documentation
        ("WINWORD.EXE", "Document1 - Word", "documentation"),
        ("notion.exe", "My Notes - Notion", "documentation"),
        # design
        ("figma.exe", "Design System - Figma", "design"),
        # fallback
        ("explorer.exe", "This PC", "other"),
        ("calc.exe", "Calculator", "other"),
        ("", "", "other"),
    ],
)
def test_classify(process_name: str, window_title: str, expected: str) -> None:
    result = classify(process_name, window_title)
    assert result == expected, f"Expected '{expected}', got {result!r} for process={process_name!r} title={window_title!r}"


def test_classify_is_case_insensitive() -> None:
    """Matching must work regardless of case in both inputs."""
    assert classify("PYCHARM64.EXE", "MAIN.PY - PROJECT") == "coding"
    assert classify("Chrome.Exe", "GOOGLE CHROME") == "browsing"
