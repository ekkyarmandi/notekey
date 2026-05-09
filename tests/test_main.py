"""Tests for the CLI commands in ``notekey.main``."""

from pathlib import Path

import pytest

from main import _display_file, _display_search_results, _parse_filter, _search_files, build_parser


# ---------------------------------------------------------------------------
#  Fixtures: a mini vault with several .md files
# ---------------------------------------------------------------------------


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Create a small vault directory with several markdown files."""
    root = tmp_path / "vault"
    root.mkdir()

    # File A: has tags "python" and "web", mentions "flask"
    (root / "flask-app.md").write_text(
        """\
---
title: Flask App
tags: [python, web]
---
# Flask App

Building a web app with #flask.
"""
    )

    # File B: has tags "python" and "data", mentions "pandas"
    (root / "pandas-guide.md").write_text(
        """\
---
title: Pandas Guide
tags: [python, data]
---
# Pandas Guide

Working with #pandas and dataframes.
"""
    )

    # File C: has tags "javascript" and "web", mentions "react"
    (root / "react-setup.md").write_text(
        """\
---
title: React Setup
tags: [javascript, web]
---
# React Setup

Getting started with #react.
"""
    )

    # File D: no frontmatter tags, but has inline #tag, no frontmatter
    (root / "scratchpad.md").write_text(
        """\
# Scratchpad

Random thoughts and #ideas.
"""
    )

    # File E: in subdirectory
    sub = root / "deep"
    sub.mkdir()
    (sub / "hidden-note.md").write_text(
        """\
---
title: Hidden
tags: [python, devops]
---
Hidden note about #docker and #kubernetes.
"""
    )

    return root


# ---------------------------------------------------------------------------
#  _parse_filter
# ---------------------------------------------------------------------------


class TestParseFilter:
    def test_substring_default(self) -> None:
        assert _parse_filter("python") == (False, "python")

    def test_exact_with_equals(self) -> None:
        assert _parse_filter("=python") == (True, "python")

    def test_exact_preserves_spaces(self) -> None:
        assert _parse_filter("= hello world") == (True, " hello world")

    def test_empty_string(self) -> None:
        assert _parse_filter("") == (False, "")

    def test_just_equals(self) -> None:
        assert _parse_filter("=") == (True, "")


# ---------------------------------------------------------------------------
#  _search_files
# ---------------------------------------------------------------------------


class TestSearchFiles:
    def test_no_filters_returns_all_md_files(self, vault: Path) -> None:
        results = _search_files(vault)
        # 5 .md files across the vault (4 in root + 1 in deep/)
        names = {md.name for md in results}
        assert names == {"flask-app", "pandas-guide", "react-setup", "scratchpad", "hidden-note"}
        assert len(results) == 5

    def test_filename_filter(self, vault: Path) -> None:
        results = _search_files(vault, filename="flask")
        assert len(results) == 1
        assert results[0].name == "flask-app"

    def test_filename_case_insensitive(self, vault: Path) -> None:
        results = _search_files(vault, filename="FLASK")
        assert len(results) == 1
        assert results[0].name == "flask-app"

    def test_filename_partial(self, vault: Path) -> None:
        results = _search_files(vault, filename="note")
        assert {md.name for md in results} == {"hidden-note"}

    def test_tags_single(self, vault: Path) -> None:
        results = _search_files(vault, tags=["python"])
        names = {md.name for md in results}
        assert names == {"flask-app", "pandas-guide", "hidden-note"}

    def test_tags_multiple_and(self, vault: Path) -> None:
        # File must have BOTH "python" AND "web"
        results = _search_files(vault, tags=["python", "web"])
        names = {md.name for md in results}
        assert names == {"flask-app"}

    def test_tags_no_match(self, vault: Path) -> None:
        results = _search_files(vault, tags=["nonexistent"])
        assert results == []

    def test_tags_case_insensitive(self, vault: Path) -> None:
        results = _search_files(vault, tags=["PYTHON"])
        assert len(results) == 3

    def test_tags_substring_match(self, vault: Path) -> None:
        """``--tags py`` matches files whose tags contain \"py\" (e.g. python)."""
        results = _search_files(vault, tags=["py"])
        names = {md.name for md in results}
        # "py" matches "python" (flask-app, pandas-guide, hidden-note)
        # and also matches "javascript"... wait, doesn't contain "py"
        # "py" is substring of "python" and "pytorch" but none of our test files have pytorch
        assert "flask-app" in names
        assert "pandas-guide" in names
        assert "hidden-note" in names
        # "react-setup" has tags [javascript, web] — neither contains "py"
        assert "react-setup" not in names

    def test_content_filter(self, vault: Path) -> None:
        results = _search_files(vault, content="pandas")
        assert len(results) == 1
        assert results[0].name == "pandas-guide"

    def test_content_case_insensitive(self, vault: Path) -> None:
        results = _search_files(vault, content="FLASK")
        assert len(results) == 1
        assert results[0].name == "flask-app"

    def test_content_no_match(self, vault: Path) -> None:
        results = _search_files(vault, content="zzzzz")
        assert results == []

    def test_content_searches_full_content_including_frontmatter(
        self, vault: Path
    ) -> None:
        # "Flask App" appears in the frontmatter title, not the body
        results = _search_files(vault, content="Flask App")
        assert len(results) == 1
        assert results[0].name == "flask-app"

    def test_content_and_tags_combined(self, vault: Path) -> None:
        # File must have "python" tag AND mention "data" in content
        results = _search_files(vault, tags=["python"], content="data")
        assert len(results) == 1
        assert results[0].name == "pandas-guide"

    def test_content_and_filename_combined(self, vault: Path) -> None:
        results = _search_files(vault, filename="flask", content="web")
        assert len(results) == 1
        assert results[0].name == "flask-app"

    def test_inline_tags_match(self, vault: Path) -> None:
        """File D has no frontmatter tags but has #ideas inline."""
        results = _search_files(vault, tags=["ideas"])
        assert len(results) == 1
        assert results[0].name == "scratchpad"

    def test_search_subdirectory(self, vault: Path) -> None:
        """Search within a subdirectory only."""
        sub = vault / "deep"
        results = _search_files(sub)
        assert len(results) == 1
        assert results[0].name == "hidden-note"

    def test_empty_directory(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        results = _search_files(empty)
        assert results == []

    def test_non_md_files_ignored(self, vault: Path) -> None:
        (vault / "notes.txt").write_text("text")
        (vault / "readme").write_text("text")
        results = _search_files(vault)
        names = {md.name for md in results}
        assert "notes" not in names
        assert "readme" not in names

    # -- exact-match tests ------------------------------------------------

    def test_tags_exact_match(self, vault: Path) -> None:
        """``--tags "=python"`` matches only files with exactly the tag "python"."""
        results = _search_files(vault, tags=["=python"])
        names = {md.name for md in results}
        assert "flask-app" in names
        assert "pandas-guide" in names
        assert "hidden-note" in names

    def test_tags_exact_no_substring(self, vault: Path) -> None:
        """``--tags "=py"`` does NOT match files with tag "python"."""
        results = _search_files(vault, tags=["=py"])
        assert results == []

    def test_tags_exact_no_match(self, vault: Path) -> None:
        results = _search_files(vault, tags=["=nonexistent"])
        assert results == []

    def test_filename_exact(self, vault: Path) -> None:
        """``--filename "=flask-app"`` matches only that exact filename."""
        results = _search_files(vault, filename="=flask-app")
        assert len(results) == 1
        assert results[0].name == "flask-app"

    def test_filename_exact_no_substring(self, vault: Path) -> None:
        """``--filename "=flask"`` does NOT match "flask-app"."""
        results = _search_files(vault, filename="=flask")
        assert results == []

    def test_content_exact(self, vault: Path) -> None:
        """Exact content matches the *full* raw file."""
        full_content = (vault / "react-setup.md").read_text()
        results = _search_files(vault, content=f"={full_content}")
        assert len(results) == 1
        assert results[0].name == "react-setup"

    def test_content_exact_no_partial(self, vault: Path) -> None:
        """``--content "=React"`` does NOT match files containing "React"."""
        results = _search_files(vault, content="=React")
        assert results == []

    # -- path-based filename matching -------------------------------------

    def test_filename_substring_path(self, vault: Path) -> None:
        """``-f "deep/hidden-note"`` matches via relative path."""
        results = _search_files(vault, filename="deep/hidden-note")
        assert len(results) == 1
        assert results[0].name == "hidden-note"

    def test_filename_substring_path_with_ext(self, vault: Path) -> None:
        """``-f "deep/hidden-note.md"`` matches with extension."""
        results = _search_files(vault, filename="deep/hidden-note.md")
        assert len(results) == 1
        assert results[0].name == "hidden-note"

    def test_filename_exact_path(self, vault: Path) -> None:
        """``-f "=deep/hidden-note"`` exact-match on relative path (no ext)."""
        results = _search_files(vault, filename="=deep/hidden-note")
        assert len(results) == 1
        assert results[0].name == "hidden-note"

    def test_filename_exact_path_with_ext(self, vault: Path) -> None:
        """``-f "=deep/hidden-note.md"`` exact-match with extension."""
        results = _search_files(vault, filename="=deep/hidden-note.md")
        assert len(results) == 1
        assert results[0].name == "hidden-note"


# ---------------------------------------------------------------------------
#  _display_search_results  (smoke tests)
# ---------------------------------------------------------------------------


class TestDisplaySearchResults:
    def test_no_results(self, capsys: pytest.CaptureFixture) -> None:
        _display_search_results([], Path.cwd())
        captured = capsys.readouterr()
        assert "No matching files found" in captured.out

    def test_with_results(self, vault: Path, capsys: pytest.CaptureFixture) -> None:
        from markdown import Markdown

        md = Markdown(vault / "flask-app.md")
        _display_search_results([md], vault)
        captured = capsys.readouterr()
        assert "flask-app.md" in captured.out
        assert "python" in captured.out
        assert "web" in captured.out


# ---------------------------------------------------------------------------
#  _display_file  (smoke tests)
# ---------------------------------------------------------------------------


class TestDisplayFile:
    def test_outputs_full_raw_content(
        self, vault: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from markdown import Markdown

        md = Markdown(vault / "flask-app.md")
        _display_file(md, vault)
        captured = capsys.readouterr()
        # Should be the exact raw file content
        assert "Building a web app with #flask." in captured.out
        assert "---" in captured.out

    def test_no_extra_output(
        self, vault: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from markdown import Markdown

        raw = (vault / "flask-app.md").read_text()
        md = Markdown(vault / "flask-app.md")
        _display_file(md, vault)
        captured = capsys.readouterr()
        # Output is exactly the raw content, nothing else
        assert captured.out == raw


# ---------------------------------------------------------------------------
#  build_parser  (structure checks)
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_search_subcommand_registered(self) -> None:
        parser = build_parser()
        # Verify the search subcommand exists by parsing
        args = parser.parse_args(["search"])
        assert args.command == "search"

    def test_search_path_default(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["search"])
        # Default is None; _resolve_path in main() handles env-var fallback.
        assert args.path is None

    def test_search_accepts_all_flags(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["search", "/some/path", "--tags", "a,b", "--filename", "test", "--content", "hello"]
        )
        assert args.path == "/some/path"
        assert args.tags == "a,b"
        assert args.filename == "test"
        assert args.content == "hello"

    def test_init_parser_unchanged(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["init", "-t", "foo,bar", "--force", "/tmp"])
        assert args.command == "init"
        assert args.tags == "foo,bar"
        assert args.force is True
        assert args.path == "/tmp"

    def test_read_subcommand_registered(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["read", "my-note"])
        assert args.command == "read"
        assert args.filename == "my-note"

    def test_read_filename_is_required(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["read"])
