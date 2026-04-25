"""Heuristic task classification from process name and window title.

Two-pass approach: process name is checked first (authoritative), then window
title (supplementary context). Add new rules by appending to the relevant list.
"""

# Pass 1: match against the executable name only. More reliable than title parsing.
_PROCESS_RULES: list[tuple[list[str], str]] = [
    (["pycharm", "idea", "rider", "clion", "goland", "webstorm", "datagrip"], "coding"),
    (["code.exe", "vscode", "vim", "nvim", "sublime_text", "notepad++", "atom", "eclipse", "netbeans"], "coding"),
    (["chrome", "firefox", "msedge", "brave", "opera", "safari", "vivaldi", "iexplore"], "browsing"),
    (["cmd", "powershell", "windowsterminal", "bash", "wsl", "mintty", "conhost", "alacritty"], "terminal"),
    (["teams", "slack", "discord", "outlook", "zoom", "skype", "telegram", "whatsapp", "mattermost"], "communication"),
    (["winword", "powerpnt", "excel", "onenote", "notion", "obsidian", "libreoffice", "writer"], "documentation"),
    (["figma", "xd", "photoshop", "illustrator", "inkscape", "gimp", "canva", "sketch"], "design"),
    (["sourcetree", "gitkraken", "tortoisegit"], "version_control"),
]

# Pass 2: fall through to window title matching when process name gives no result.
_TITLE_RULES: list[tuple[list[str], str]] = [
    (["github", "gitlab", "bitbucket", "git commit", "git push"], "version_control"),
    (["jira", "confluence", "trello", "asana", "linear"], "documentation"),
    (["stackoverflow", "stack overflow", "mdn web docs", "docs.python"], "browsing"),
]


def classify(process_name: str, window_title: str) -> str:
    """Return the work category for a given process name and window title.

    Process name takes priority: if the executable matches a known category,
    that result is returned without inspecting the title. This prevents titles
    like "GitHub - Microsoft Edge" from being misclassified as version_control.

    Args:
        process_name: Executable name, e.g. "pycharm64.exe".
        window_title: Window title string, e.g. "main.py - MyProject".

    Returns:
        Category string such as "coding", "browsing", or "other".
    """
    proc_lower = process_name.lower()
    for keywords, category in _PROCESS_RULES:
        if any(kw in proc_lower for kw in keywords):
            return category

    title_lower = window_title.lower()
    for keywords, category in _TITLE_RULES:
        if any(kw in title_lower for kw in keywords):
            return category

    return "other"
