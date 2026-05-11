"""Tests for the ``Markdown`` class in ``notekey.markdown``."""

import datetime
from pathlib import Path

import pytest

from notekey.markdown import Markdown, Section
from notekey.utils import (
    extract_inline_tags,
    extract_markdown_links,
    extract_wiki_links,
    normalize_size,
)

# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_md(tmp_path: Path) -> Path:
    """Create a temporary markdown file with frontmatter, tags, and links."""
    content = """\
---
title: Test Note
tags: [project, documentation, obsidian]
created: 2024-01-15
status: active
aliases:
---

# Test Note

This is a test markdown file.

Inline tags like #python and #testing should be detected.

Nested tags like #project/active and #topic/obsidian/plugins.

Wiki links:
- [[another-note]]
- [[note with spaces]]
- [[target-note|Display Text]]
- [[page]]

Markdown links:
- [External Link](https://example.com)
- [Relative Link](./another-page.md)
"""
    path = tmp_path / "test-note.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_md_no_frontmatter(tmp_path: Path) -> Path:
    """Create a markdown file *without* frontmatter."""
    content = """\
# Plain Note

A note with no frontmatter.

Tags: #plain and #simple.
"""
    path = tmp_path / "plain.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_md_tags_in_frontmatter_only(tmp_path: Path) -> Path:
    """Markdown file whose tags appear only in frontmatter YAML list
    syntax (not inline)."""
    content = """\
---
title: Tagged
tags:
  - alpha
  - beta
---
Body text with no inline tags.
"""
    path = tmp_path / "tagged-frontmatter.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_md_untagged(tmp_path: Path) -> Path:
    """A markdown file with no tags or links at all."""
    content = """\
# Untagged

Just text.
"""
    path = tmp_path / "untagged.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def sample_md_long_body(tmp_path: Path) -> Path:
    """A markdown file long enough to register a meaningful read time."""
    words = ("word " * 600).strip()
    content = f"""\
---
title: Long
---
{words}
"""
    path = tmp_path / "long.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
#  extract_inline_tags
# ---------------------------------------------------------------------------


class TestExtractInlineTags:
    def test_simple_tags(self) -> None:
        tags = extract_inline_tags("#python and #testing")
        assert tags == {"python", "testing"}

    def test_nested_tags(self) -> None:
        tags = extract_inline_tags("#project/active and #topic/obsidian/plugins")
        assert tags == {"project/active", "topic/obsidian/plugins"}

    def test_pure_numeric_not_extracted(self) -> None:
        tags = extract_inline_tags("this is #123 not a tag")
        assert "123" not in tags

    def test_no_false_positive_inside_code_block(self) -> None:
        text = "```\n#comment\n```"
        tags = extract_inline_tags(text)
        assert "comment" not in tags

    def test_no_tags_returns_empty(self) -> None:
        tags = extract_inline_tags("Plain text with no tags.")
        assert tags == set()


# ---------------------------------------------------------------------------
#  extract_wiki_links
# ---------------------------------------------------------------------------


class TestExtractWikiLinks:
    def test_basic_wiki_link(self) -> None:
        links = extract_wiki_links("Link to [[another-note]] here.")
        assert links == {"another-note"}

    def test_wiki_link_with_display(self) -> None:
        links = extract_wiki_links("[[target|Display Text]]")
        assert links == {"target"}

    def test_wiki_link_with_spaces(self) -> None:
        links = extract_wiki_links("[[note with spaces]]")
        assert links == {"note with spaces"}

    def test_multiple_wiki_links(self) -> None:
        links = extract_wiki_links("[[a]] and [[b]] and [[c]]")
        assert links == {"a", "b", "c"}

    def test_no_links(self) -> None:
        links = extract_wiki_links("No links here.")
        assert links == set()


# ---------------------------------------------------------------------------
#  extract_markdown_links
# ---------------------------------------------------------------------------


class TestExtractMarkdownLinks:
    def test_external_url(self) -> None:
        links = extract_markdown_links("[Example](https://example.com)")
        assert links == {"https://example.com"}

    def test_relative_path(self) -> None:
        links = extract_markdown_links("[Local](./page.md)")
        assert links == {"./page.md"}

    def test_no_links(self) -> None:
        links = extract_markdown_links("No links.")
        assert links == set()


# ---------------------------------------------------------------------------
#  normalize_size
# ---------------------------------------------------------------------------


class TestNormalizeSize:
    def test_bytes(self) -> None:
        assert normalize_size(500) == "500 B"

    def test_kilobytes(self) -> None:
        assert normalize_size(2048) == "2.0 KB"

    def test_megabytes(self) -> None:
        assert normalize_size(5_242_880) == "5.0 MB"

    def test_gigabytes(self) -> None:
        assert normalize_size(3_221_225_472) == "3.00 GB"

    def test_zero_bytes(self) -> None:
        assert normalize_size(0) == "0 B"


# ---------------------------------------------------------------------------
#  Markdown class – construction and errors
# ---------------------------------------------------------------------------


class TestMarkdownInit:
    def test_load_success(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        assert md.name == "test-note"
        assert isinstance(md.size, float)
        assert md.size > 0
        assert isinstance(md.created_at, datetime.datetime)
        assert isinstance(md.updated_at, datetime.datetime)
        assert isinstance(md.reading_time, str)
        assert "min" in md.reading_time or "sec" in md.reading_time

    def test_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError, match="File not found"):
            Markdown("/nonexistent/file.md")

    def test_directory_instead_of_file(self, tmp_path: Path) -> None:
        with pytest.raises(IsADirectoryError, match="not a file"):
            Markdown(tmp_path)


# ---------------------------------------------------------------------------
#  Markdown – tags
# ---------------------------------------------------------------------------


class TestMarkdownTags:
    def test_tags_combined_from_frontmatter_and_inline(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        # frontmatter: project, documentation, obsidian
        # inline: python, testing, project/active, topic/obsidian/plugins
        assert "python" in md.tags
        assert "testing" in md.tags
        assert "project" in md.tags
        assert "documentation" in md.tags
        assert "obsidian" in md.tags
        assert "project/active" in md.tags
        assert "topic/obsidian/plugins" in md.tags

    def test_tags_from_frontmatter_list_syntax(
        self, sample_md_tags_in_frontmatter_only: Path
    ) -> None:
        md = Markdown(sample_md_tags_in_frontmatter_only)
        assert md.tags == ["alpha", "beta"]

    def test_tags_from_frontmatter_string(self, tmp_path: Path) -> None:
        path = tmp_path / "string-tag.md"
        path.write_text("---\ntags: alpha\n---\nBody", encoding="utf-8")
        md = Markdown(path)
        assert md.tags == ["alpha"]

    def test_no_tags(self, sample_md_untagged: Path) -> None:
        md = Markdown(sample_md_untagged)
        assert md.tags == []

    def test_no_frontmatter_still_gets_inline_tags(
        self, sample_md_no_frontmatter: Path
    ) -> None:
        md = Markdown(sample_md_no_frontmatter)
        assert "plain" in md.tags
        assert "simple" in md.tags


# ---------------------------------------------------------------------------
#  Markdown – links
# ---------------------------------------------------------------------------


class TestMarkdownLinks:
    def test_wiki_links(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        assert "another-note" in md.links
        assert "note with spaces" in md.links
        assert "target-note" in md.links
        assert "page" in md.links

    def test_markdown_links(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        assert "https://example.com" in md.links
        assert "./another-page.md" in md.links

    def test_no_links(self, sample_md_untagged: Path) -> None:
        md = Markdown(sample_md_untagged)
        assert md.links == []


# ---------------------------------------------------------------------------
#  Markdown – metadata
# ---------------------------------------------------------------------------


class TestMarkdownMetadata:
    def test_frontmatter_metadata(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        assert md.metadata["title"] == "Test Note"
        assert md.metadata["created"] == datetime.date(2024, 1, 15)
        assert md.metadata["status"] == "active"

    def test_no_frontmatter_metadata(self, sample_md_no_frontmatter: Path) -> None:
        md = Markdown(sample_md_no_frontmatter)
        assert md.metadata == {}

    def test_content_is_preserved(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        assert md.content.startswith("---")
        assert "# Test Note" in md.content
        assert "Inline tags like" in md.content


# ---------------------------------------------------------------------------
#  Markdown – sections
# ---------------------------------------------------------------------------


class TestMarkdownSections:
    def test_sections_from_frontmatter_file_use_markdown_line_index(
        self, sample_md: Path
    ) -> None:
        md = Markdown(sample_md)
        assert md.sections[0] == Section(
            title="Test Note",
            heading=1,
            content=(
                "This is a test markdown file.\n\n"
                "Inline tags like #python and #testing should be detected.\n\n"
                "Nested tags like #project/active and #topic/obsidian/plugins.\n\n"
                "Wiki links:\n"
                "- [[another-note]]\n"
                "- [[note with spaces]]\n"
                "- [[target-note|Display Text]]\n"
                "- [[page]]\n\n"
                "Markdown links:\n"
                "- [External Link](https://example.com)\n"
                "- [Relative Link](./another-page.md)"
            ),
            index=8,
        )

    def test_sections_include_nested_heading_levels(self, tmp_path: Path) -> None:
        path = tmp_path / "sections.md"
        path.write_text(
            "# First ###\n\n"
            "First paragraph.\n\n"
            "## Second\n\n"
            "Second paragraph.\n\n"
            "###### Sixth\n",
            encoding="utf-8",
        )
        md = Markdown(path)
        assert md.sections == [
            Section(
                title="First",
                heading=1,
                content="First paragraph.",
                index=0,
            ),
            Section(
                title="Second",
                heading=2,
                content="Second paragraph.",
                index=4,
            ),
            Section(title="Sixth", heading=6, content="", index=8),
        ]

    def test_sections_ignore_headings_inside_fenced_code(self, tmp_path: Path) -> None:
        path = tmp_path / "fenced.md"
        path.write_text(
            "# Real\n\n"
            "```markdown\n"
            "## Not a section\n"
            "```\n\n"
            "## After\n\n"
            "Body.",
            encoding="utf-8",
        )
        md = Markdown(path)
        assert [section.title for section in md.sections] == ["Real", "After"]
        assert "## Not a section" in md.sections[0].content

    def test_no_heading_returns_empty_sections(
        self, sample_md_tags_in_frontmatter_only: Path
    ) -> None:
        md = Markdown(sample_md_tags_in_frontmatter_only)
        assert md.sections == []


# ---------------------------------------------------------------------------
#  Markdown – reading time
# ---------------------------------------------------------------------------


class TestMarkdownReadingTime:
    def test_reading_time_attribute(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        assert isinstance(md.reading_time, str)

    def test_reading_time_format(self, sample_md_long_body: Path) -> None:
        md = Markdown(sample_md_long_body)
        # Should be something like "2 min read"
        assert "min" in md.reading_time or "sec" in md.reading_time

    def test_short_content_read_time(self, sample_md_no_frontmatter: Path) -> None:
        md = Markdown(sample_md_no_frontmatter)
        assert isinstance(md.reading_time, str)


# ---------------------------------------------------------------------------
#  Markdown – _normalize_size
# ---------------------------------------------------------------------------


class TestMarkdownNormalizeSize:
    def test_human_readable_size(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        result = md._normalize_size()
        # Should be something like "1.2 KB" or "1234 B"
        assert isinstance(result, str)
        assert any(result.endswith(suffix) for suffix in ("B", "KB", "MB", "GB"))

    def test_zero_size(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.md"
        path.write_text("", encoding="utf-8")
        md = Markdown(path)
        assert md._normalize_size() == "0 B"


# ---------------------------------------------------------------------------
#  Markdown – write
# ---------------------------------------------------------------------------


class TestMarkdownWrite:
    def test_write_persists_content(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        original = md.content
        md.write()
        assert sample_md.read_text(encoding="utf-8") == original

    def test_write_with_custom_content(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        new_content = "# New Content\n\nOverwritten.\n"
        md.write(new_content)
        assert sample_md.read_text(encoding="utf-8") == new_content
        assert md.content == new_content

    def test_write_refreshes_derived_attributes(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        md.write("# New Content\n\nSee [[target]] and #updated.\n")
        assert md.metadata == {}
        assert md.tags == ["updated"]
        assert md.links == ["target"]
        assert md.sections == [
            Section(
                title="New Content",
                heading=1,
                content="See [[target]] and #updated.",
                index=0,
            )
        ]

    def test_write_updates_size_and_mtime(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        old_updated = md.updated_at
        old_size = md.size
        new_content = "short"
        md.write(new_content)
        assert md.size != old_size
        assert md.updated_at > old_updated


# ---------------------------------------------------------------------------
#  Markdown – __repr__
# ---------------------------------------------------------------------------


class TestMarkdownRepr:
    def test_repr_format(self, sample_md: Path) -> None:
        md = Markdown(sample_md)
        rep = repr(md)
        assert rep.startswith("<Markdown filename='")
        assert rep.endswith(">")
        assert md.name in rep
        assert "size=" in rep

    def test_repr_untagged(self, sample_md_untagged: Path) -> None:
        md = Markdown(sample_md_untagged)
        rep = repr(md)
        assert md.name in rep
