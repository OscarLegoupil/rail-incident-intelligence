from __future__ import annotations


def normalize_text(raw_text: str) -> str:
    """Normalize text for ingestion while preserving readable structure."""
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    collapsed_lines: list[str] = []
    blank_run = 0

    for line in lines:
        stripped = line.rstrip()
        if stripped == "":
            blank_run += 1
            if blank_run <= 1:
                collapsed_lines.append("")
        else:
            blank_run = 0
            collapsed_lines.append(stripped)

    while collapsed_lines and collapsed_lines[0] == "":
        collapsed_lines.pop(0)
    while collapsed_lines and collapsed_lines[-1] == "":
        collapsed_lines.pop()

    return "\n".join(collapsed_lines)
