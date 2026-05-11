import datetime
import re
from dataclasses import dataclass
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


_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")


@dataclass(frozen=True)
class Section:
    """A heading-delimited section in a Markdown document."""

    title: str
    heading: int
    content: str
    index: int


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
    sections: list[Section]
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
        self._parse_content()

    def _parse_content(self) -> None:
        """Parse the raw markdown content into derived attributes."""

        # Parse frontmatter via python-frontmatter.
        post: Any = frontmatter.loads(self.content)
        self.metadata = dict(post.metadata)
        self._body: str = post.content  # body *without* frontmatter

        # Reading time estimated from the body content.
        self._reading_time_result = readtime.of_markdown(self._body)
        self.reading_time = str(self._reading_time_result)

        self.tags = self._get_tags()
        self.links = self._get_links()
        self.sections = self._get_sections()

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

    def _body_start_index(self) -> int:
        """Return the zero-based line index where markdown body content starts."""
        lines = self.content.splitlines()
        if not lines or lines[0].strip() != "---":
            return 0
        return next(
            (
                index + 1
                for index, line in enumerate(lines[1:], start=1)
                if line.strip() in {"---", "..."}
            ),
            0,
        )

    @staticmethod
    def _clean_heading_title(title: str) -> str:
        """Trim heading text and optional closing ATX hash markers."""
        return re.sub(r"[ \t]+#+[ \t]*$", "", title.strip()).strip()

    @staticmethod
    def _section_content(lines: list[str]) -> str:
        """Return section lines without surrounding blank lines."""
        start = 0
        end = len(lines)
        while start < end and not lines[start].strip():
            start += 1
        while end > start and not lines[end - 1].strip():
            end -= 1
        return "\n".join(lines[start:end])

    def _get_sections(self) -> list[Section]:
        """Extract top-level and nested heading sections from the markdown body."""
        lines = self.content.splitlines()
        body_start = self._body_start_index()
        sections: list[Section] = []
        current: Section | None = None
        current_lines: list[str] = []
        in_fence = False
        fence_marker = ""

        for index, line in enumerate(lines[body_start:], start=body_start):
            stripped = line.lstrip()
            fence_match = re.match(r"^(```+|~~~+)", stripped)
            if fence_match:
                marker = fence_match.group(1)
                if not in_fence:
                    in_fence = True
                    fence_marker = marker[0]
                elif marker.startswith(fence_marker):
                    in_fence = False
                    fence_marker = ""

            heading_match = None if in_fence else _HEADING_RE.match(line)
            if heading_match:
                if current is not None:
                    sections.append(
                        Section(
                            title=current.title,
                            heading=current.heading,
                            content=self._section_content(current_lines),
                            index=current.index,
                        )
                    )

                marker, title = heading_match.groups()
                current = Section(
                    title=self._clean_heading_title(title),
                    heading=len(marker),
                    content="",
                    index=index,
                )
                current_lines = []
                continue

            if current is not None:
                current_lines.append(line)

        if current is not None:
            sections.append(
                Section(
                    title=current.title,
                    heading=current.heading,
                    content=self._section_content(current_lines),
                    index=current.index,
                )
            )

        return sections

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
        self._parse_content()

    def __repr__(self) -> str:
        return f"<Markdown filename='{self.name}' size='{self._normalize_size()}'>"
