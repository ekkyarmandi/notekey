import datetime
from pathlib import Path
from typing import Any

import frontmatter
import readtime

from notekey.utils import (
    extract_inline_tags,
    extract_markdown_links,
    extract_wiki_links,
    normalize_size,
)


class Markdown:
    """Represents a parsed Markdown file from an Obsidian vault.

    Uses ``python-frontmatter`` for frontmatter parsing and ``readtime``
    for reading-time estimation.
    """

    created_at: datetime.datetime
    updated_at: datetime.datetime
    name: str
    size: float
    metadata: dict
    content: str
    tags: list[str]
    links: list[str]
    reading_time: str

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).expanduser().resolve()

        if not self._path.exists():
            raise FileNotFoundError(f"File not found: {self._path}")
        if not self._path.is_file():
            raise IsADirectoryError(f"Path is not a file: {self._path}")

        stat = self._path.stat()
        self.name = self._path.stem
        self._size_bytes: float = float(stat.st_size)
        self.size = self._size_bytes
        created_ts = getattr(stat, "st_birthtime", stat.st_ctime)
        self.created_at = datetime.datetime.fromtimestamp(created_ts)
        self.updated_at = datetime.datetime.fromtimestamp(stat.st_mtime)

        # Full raw content (frontmatter + body) — needed for link extraction.
        self.content = self._path.read_text(encoding="utf-8")

        # Parse frontmatter via python-frontmatter.
        post: Any = frontmatter.loads(self.content)
        self.metadata = dict(post.metadata)
        self._body: str = post.content  # body *without* frontmatter

        # Reading time estimated from the body content.
        self._reading_time_result = readtime.of_markdown(self._body)
        self.reading_time = str(self._reading_time_result)

        self.tags = self._get_tags()
        self.links = self._get_links()

    def _get_tags(self) -> list[str]:
        """Extract tags from frontmatter *and* inline ``#tag`` references."""
        tags: set[str] = set()

        # Tags from frontmatter
        fm_tags = self.metadata.get("tags", [])
        if isinstance(fm_tags, list):
            tags.update(str(t).strip() for t in fm_tags if t)
        elif isinstance(fm_tags, str):
            tags.add(fm_tags.strip())

        # Tags from body content (#tag syntax)
        tags.update(extract_inline_tags(self._body))

        return sorted(tags)

    def _get_links(self) -> list[str]:
        """Extract wiki links and markdown links from the file content."""
        links: set[str] = set()
        links.update(extract_wiki_links(self.content))
        links.update(extract_markdown_links(self.content))
        return sorted(links)

    def _normalize_size(self) -> str:
        """Return the file size as a human-readable string."""
        return normalize_size(self._size_bytes)

    def write(self, content: str | None = None) -> None:
        """Write content back to the markdown file.

        If *content* is given it replaces ``self.content``; otherwise
        ``self.content`` is written as-is.
        """
        if content is not None:
            self.content = content
        self._path.write_text(self.content, encoding="utf-8")
        stat = self._path.stat()
        self._size_bytes = float(stat.st_size)
        self.size = self._size_bytes
        self.updated_at = datetime.datetime.fromtimestamp(stat.st_mtime)

    def __repr__(self) -> str:
        return f"<Markdown filename='{self.name}' size='{self._normalize_size()}'>"
