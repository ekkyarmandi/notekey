"""Utility functions for markdown parsing and formatting."""

import re


def extract_inline_tags(text: str) -> set[str]:
    """Extract inline ``#tag`` references from *text*.

    Matches ``#tag``, ``#tag/subtag``, etc. while avoiding false
    positives inside fenced code blocks, inline code spans,
    markdown links, or hex colours.
    """
    # Strip fenced code blocks first so tags inside them are ignored.
    body = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Strip inline code spans as well.
    body = re.sub(r"`[^`]+`", "", body)

    tags: set[str] = set()

    # Match #identifier (with optional /path).  The tag body cannot
    # contain a trailing period so that ``#tag.`` correctly yields ``tag``.
    pattern = re.compile(
        r"(?:^|(?<=\s))"
        r"#([a-zA-Z_][a-zA-Z0-9_/-]*)"
        r"(?=\s|$|[.,;:!?)])"
    )

    for match in pattern.finditer(body):
        tag = match.group(1)
        # Skip pure numeric tags (e.g. #123)
        if not any(c.isalpha() for c in tag):
            continue
        tags.add(tag)

    return tags


def extract_wiki_links(text: str) -> set[str]:
    """Extract Obsidian wiki-link targets from *text*.

    Handles ``[[target]]`` and ``[[target|display text]]``.
    """
    links: set[str] = set()
    pattern = re.compile(r"\[\[([^\[\]]+?)(?:\|[^\[\]]*)?\]\]")
    for match in pattern.finditer(text):
        target = match.group(1).strip()
        # Skip empty / anchor-only links
        if target:
            links.add(target)
    return links


def extract_markdown_links(text: str) -> set[str]:
    """Extract markdown-style links from *text*.

    Handles ``[text](url)``, excluding reference-style links.
    """
    links: set[str] = set()
    pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
    for match in pattern.finditer(text):
        url = match.group(2).strip()
        if url:
            links.add(url)
    return links


def normalize_size(size_bytes: int | float) -> str:
    """Convert a byte count to a human-readable string."""
    size = float(size_bytes)
    if size < 1024:
        return f"{size:.0f} B"
    elif size < 1024**2:
        return f"{size / 1024:.1f} KB"
    elif size < 1024**3:
        return f"{size / 1024**2:.1f} MB"
    else:
        return f"{size / 1024**3:.2f} GB"
