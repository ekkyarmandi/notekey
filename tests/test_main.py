"""Tests for the CLI commands in ``notekey.main``."""

import runpy
import sys
from pathlib import Path

import pytest

import notekey.main as main_module

from notekey.main import (
    _build_filters,
    _compute_backlinks,
    _compute_stats,
    _compute_tags,
    _create_base,
    _create_markdown,
    _display_backlinks,
    _display_file,
    _display_search_results,
    _display_stats,
    _display_tags,
    _filename_candidates,
    _find_vault_root,
    _get_folder,
    _json_serializable,
    _open_in_obsidian,
    _parse_filter,
    _relative_to_vault,
    _resolve_path,
    _search_files,
    build_parser,
    main,
)

# ---------------------------------------------------------------------------
#  Fixtures: a mini vault with several .md files
# ---------------------------------------------------------------------------


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """Create a small vault directory with several markdown files."""
    root = tmp_path / "vault"
    root.mkdir()
    (root / ".obsidian").mkdir()

    # File A: has tags "python" and "web", mentions "flask"
    (root / "flask-app.md").write_text("""\
---
title: Flask App
tags: [python, web]
---
# Flask App

Building a web app with #flask.
""")

    # File B: has tags "python" and "data", mentions "pandas"
    (root / "pandas-guide.md").write_text("""\
---
title: Pandas Guide
tags: [python, data]
---
# Pandas Guide

Working with #pandas and dataframes.
""")

    # File C: has tags "javascript" and "web", mentions "react"
    (root / "react-setup.md").write_text("""\
---
title: React Setup
tags: [javascript, web]
---
# React Setup

Getting started with #react.
""")

    # File D: no frontmatter tags, but has inline #tag, no frontmatter
    (root / "scratchpad.md").write_text("""\
# Scratchpad

Random thoughts and #ideas.
""")

    # File E: in subdirectory
    sub = root / "deep"
    sub.mkdir()
    (sub / "hidden-note.md").write_text("""\
---
title: Hidden
tags: [python, devops]
---
Hidden note about #docker and #kubernetes.
""")

    return root


@pytest.fixture
def vault_with_links(tmp_path: Path) -> Path:
    """A small vault where notes contain wiki links to each other."""
    root = tmp_path / "vault"
    root.mkdir()
    (root / ".obsidian").mkdir()

    (root / "note-a.md").write_text("""\
---
title: Note A
tags: [alpha]
---
Links to [[note-b]] and [[note-c]].
""")

    (root / "note-b.md").write_text("""\
---
title: Note B
tags: [beta]
---
Links to [[note-a]] and [[note-c]].
""")

    (root / "note-c.md").write_text("""\
---
title: Note C
tags: [gamma]
---
No outgoing links.
""")

    (root / "note-d.md").write_text("""\
---
title: Note D
tags: [delta]
---
Links to [[note-a|Display]] and [[note-b]].
""")

    return root


# ---------------------------------------------------------------------------
#  path / vault helpers
# ---------------------------------------------------------------------------


class TestPathAndVaultHelpers:
    def test_resolve_path_explicit(self) -> None:
        assert _resolve_path("/tmp/vault") == "/tmp/vault"

    def test_resolve_path_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", "/env/vault")
        assert _resolve_path() == "/env/vault"

    def test_resolve_path_default_current_dir(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
        assert _resolve_path() == "."

    def test_get_folder_success(self, vault: Path) -> None:
        assert _get_folder(str(vault)) == vault.resolve()

    def test_get_folder_default_cwd(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(vault)
        assert _get_folder() == vault.resolve()

    def test_get_folder_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _get_folder(str(tmp_path / "missing"))

    def test_get_folder_not_directory(self, vault: Path) -> None:
        with pytest.raises(NotADirectoryError):
            _get_folder(str(vault / "flask-app.md"))

    def test_find_vault_root_from_child(self, vault: Path) -> None:
        assert _find_vault_root(vault / "deep") == vault

    def test_find_vault_root_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _find_vault_root(tmp_path)


# ---------------------------------------------------------------------------
#  init helpers
# ---------------------------------------------------------------------------


class TestInitHelpers:
    def test_build_filters_name_only(self) -> None:
        assert _build_filters("project") == '"project"'

    def test_build_filters_dedupes_and_skips_empty(self) -> None:
        assert _build_filters("project", "alpha, project, ,beta") == (
            '"project", "alpha", "beta"'
        )

    def test_create_base(self, vault: Path) -> None:
        path = _create_base(vault, "vault", tags="python", force=False)
        assert path == vault / "vault.base"
        assert path.exists()
        assert 'file.tags.containsAny("vault", "python")' in path.read_text()

    def test_create_base_existing_raises(self, vault: Path) -> None:
        _create_base(vault, "vault", force=False)
        with pytest.raises(FileExistsError):
            _create_base(vault, "vault", force=False)

    def test_create_base_force_overwrites(self, vault: Path) -> None:
        path = _create_base(vault, "vault", force=False)
        path.write_text("old")
        _create_base(vault, "vault", force=True)
        assert path.read_text() != "old"

    def test_create_markdown(self, vault: Path) -> None:
        path = _create_markdown(vault, "vault", force=False)
        assert path == vault / "vault.md"
        assert path.exists()
        assert "![[vault.base]]" in path.read_text()

    def test_create_markdown_existing_raises(self, vault: Path) -> None:
        _create_markdown(vault, "vault", force=False)
        with pytest.raises(FileExistsError):
            _create_markdown(vault, "vault", force=False)

    def test_create_markdown_force_overwrites(self, vault: Path) -> None:
        path = _create_markdown(vault, "vault", force=False)
        path.write_text("old")
        _create_markdown(vault, "vault", force=True)
        assert path.read_text() != "old"


# ---------------------------------------------------------------------------
#  filename / relative-path helpers
# ---------------------------------------------------------------------------


class TestFilenameAndRelativePathHelpers:
    def test_filename_candidates_relative(self, vault: Path) -> None:
        assert _filename_candidates(vault / "deep" / "hidden-note.md", vault) == (
            "hidden-note",
            "deep/hidden-note.md",
            "deep/hidden-note",
        )

    def test_filename_candidates_outside_vault(
        self, tmp_path: Path, vault: Path
    ) -> None:
        note = tmp_path / "outside.md"
        note.write_text("outside")
        assert _filename_candidates(note, vault) == ("outside", "outside.md", "outside")

    def test_relative_to_vault_outside_vault(self, tmp_path: Path, vault: Path) -> None:
        from notekey.markdown import Markdown

        note = tmp_path / "outside.md"
        note.write_text("outside")
        md = Markdown(note)
        assert _relative_to_vault(md, vault) == "outside.md"


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
        assert names == {
            "flask-app",
            "pandas-guide",
            "react-setup",
            "scratchpad",
            "hidden-note",
        }
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

    def test_content_read_error_is_skipped(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def raise_os_error(self: Path, *args, **kwargs) -> str:
            raise OSError("cannot read")

        monkeypatch.setattr(Path, "read_text", raise_os_error)
        assert _search_files(vault, content="anything") == []

    def test_markdown_parse_error_is_skipped(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class RaisingMarkdown:
            def __init__(self, path: Path) -> None:
                raise ValueError("bad markdown")

        monkeypatch.setattr(main_module, "Markdown", RaisingMarkdown)
        assert _search_files(vault) == []

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
        from notekey.markdown import Markdown

        md = Markdown(vault / "flask-app.md")
        _display_search_results([md], vault)
        captured = capsys.readouterr()
        assert "flask-app.md" in captured.out
        assert "python" in captured.out
        assert "web" in captured.out

    def test_json_output(self, vault: Path, capsys: pytest.CaptureFixture) -> None:
        from notekey.markdown import Markdown

        md = Markdown(vault / "flask-app.md")
        _display_search_results([md], vault, json_output=True)
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "flask-app"
        assert "python" in data[0]["tags"]
        assert "web" in data[0]["tags"]

    def test_json_output_empty(self, capsys: pytest.CaptureFixture) -> None:
        _display_search_results([], Path.cwd(), json_output=True)
        captured = capsys.readouterr()
        import json

        assert json.loads(captured.out) == []


# ---------------------------------------------------------------------------
#  _display_file  (smoke tests)
# ---------------------------------------------------------------------------


class TestDisplayFile:
    def test_outputs_full_raw_content(
        self, vault: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from notekey.markdown import Markdown

        md = Markdown(vault / "flask-app.md")
        _display_file(md, vault)
        captured = capsys.readouterr()
        # Should be the exact raw file content
        assert "Building a web app with #flask." in captured.out
        assert "---" in captured.out

    def test_no_extra_output(self, vault: Path, capsys: pytest.CaptureFixture) -> None:
        from notekey.markdown import Markdown

        raw = (vault / "flask-app.md").read_text()
        md = Markdown(vault / "flask-app.md")
        _display_file(md, vault)
        captured = capsys.readouterr()
        # Output is exactly the raw content, nothing else
        assert captured.out == raw


# ---------------------------------------------------------------------------
#  main() command branches
# ---------------------------------------------------------------------------


class TestMainCommandBranches:
    def test_main_init(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        target = vault / "new-project"
        target.mkdir()
        monkeypatch.setattr(sys, "argv", ["notekey", "init", str(target), "--force"])

        main()

        captured = capsys.readouterr()
        assert "Created base:" in captured.out
        assert (target / "new-project.base").exists()
        assert (target / "new-project.md").exists()

    def test_main_init_without_path_uses_current_directory(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        target = vault / "01-PROJECTS" / "OpenClaw"
        target.mkdir(parents=True)
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.chdir(target)
        monkeypatch.setattr(sys, "argv", ["notekey", "init", "--force"])

        main()

        captured = capsys.readouterr()
        assert f"Created base: {target / 'OpenClaw.base'}" in captured.out
        assert f"Created markdown: {target / 'OpenClaw.md'}" in captured.out
        assert (target / "OpenClaw.base").exists()
        assert (target / "OpenClaw.md").exists()
        assert not (vault / "vault.base").exists()
        assert not (vault / "vault.md").exists()

    def test_main_search_uses_obsidian_vault_default(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "search", "--tags", "python"])

        main()

        captured = capsys.readouterr()
        assert "Found 3 files" in captured.out
        assert "flask-app.md" in captured.out

    def test_main_read_no_results(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "read", "missing-note"])

        main()

        captured = capsys.readouterr()
        assert "No file found matching: missing-note" in captured.out

    def test_main_read_single_result(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "read", "=flask-app"])

        main()

        captured = capsys.readouterr()
        assert captured.out == (vault / "flask-app.md").read_text()

    def test_main_read_multiple_results(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "read", "a"])

        main()

        captured = capsys.readouterr()
        assert "Multiple matches" in captured.out

    def test_script_entrypoint(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "read", "=flask-app"])

        runpy.run_path(
            str(Path(__file__).parents[1] / "notekey" / "main.py"), run_name="__main__"
        )

        captured = capsys.readouterr()
        assert captured.out == (vault / "flask-app.md").read_text()


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
            [
                "search",
                "/some/path",
                "--tags",
                "a,b",
                "--filename",
                "test",
                "--content",
                "hello",
            ]
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


# ---------------------------------------------------------------------------
#  _json_serializable
# ---------------------------------------------------------------------------


class TestJsonSerializable:
    def test_converts_markdown_to_dict(self, vault: Path) -> None:
        from notekey.markdown import Markdown

        md = Markdown(vault / "flask-app.md")
        data = _json_serializable(md, vault)
        assert data["name"] == "flask-app"
        assert data["path"] == "flask-app.md"
        assert "python" in data["tags"]
        assert isinstance(data["size_bytes"], int)
        assert data["title"] == "Flask App"

    def test_note_outside_vault(self, vault: Path, tmp_path: Path) -> None:
        from notekey.markdown import Markdown

        path = tmp_path / "outside.md"
        path.write_text("# Outside")
        md = Markdown(path)
        data = _json_serializable(md, vault)
        assert data["path"] == "outside.md"


# ---------------------------------------------------------------------------
#  _compute_tags / _display_tags
# ---------------------------------------------------------------------------


class TestComputeTags:
    def test_computes_tag_counts(self, vault: Path) -> None:
        tags = _compute_tags(vault)
        # python: 3 (flask-app, pandas-guide, hidden-note)
        # web: 2 (flask-app, react-setup)
        # data: 1, javascript: 1, devops: 1, ...
        tag_dict = dict(tags)
        assert tag_dict["python"] == 3
        assert tag_dict["web"] == 2

    def test_empty_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        assert _compute_tags(root) == []


class TestDisplayTags:
    def test_with_results(self, vault: Path, capsys: pytest.CaptureFixture) -> None:
        tags = _compute_tags(vault)
        _display_tags(tags)
        captured = capsys.readouterr()
        assert "python" in captured.out
        assert "3" in captured.out

    def test_json_output(self, vault: Path, capsys: pytest.CaptureFixture) -> None:
        tags = _compute_tags(vault)
        _display_tags(tags, json_output=True)
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert any(d["tag"] == "python" and d["count"] == 3 for d in data)

    def test_empty(self, capsys: pytest.CaptureFixture) -> None:
        _display_tags([])
        captured = capsys.readouterr()
        assert "No tags found" in captured.out

    def test_json_empty(self, capsys: pytest.CaptureFixture) -> None:
        _display_tags([], json_output=True)
        captured = capsys.readouterr()
        import json

        assert json.loads(captured.out) == []


# ---------------------------------------------------------------------------
#  _compute_backlinks / _display_backlinks
# ---------------------------------------------------------------------------


class TestComputeBacklinks:
    def test_finds_backlinks(self, vault_with_links: Path) -> None:
        results = _compute_backlinks(vault_with_links, "note-a")
        names = {md.name for md in results}
        # note-b links to note-a, note-d links to note-a|Display
        assert "note-b" in names
        assert "note-d" in names
        # note-a does not backlink to itself
        assert "note-a" not in names
        # note-c has no links to note-a
        assert "note-c" not in names

    def test_no_backlinks(self, vault_with_links: Path) -> None:
        results = _compute_backlinks(vault_with_links, "note-c")
        # note-a links to note-c, note-b links to note-c
        assert {md.name for md in results} == {"note-a", "note-b"}

    def test_target_not_found(self, vault_with_links: Path) -> None:
        with pytest.raises(FileNotFoundError, match="missing-note"):
            _compute_backlinks(vault_with_links, "missing-note")


class TestDisplayBacklinks:
    def test_with_results(
        self, vault_with_links: Path, capsys: pytest.CaptureFixture
    ) -> None:
        results = _compute_backlinks(vault_with_links, "note-a")
        _display_backlinks(results, "note-a", vault_with_links)
        captured = capsys.readouterr()
        assert "note-b" in captured.out
        assert "note-d" in captured.out

    def test_json_output(
        self, vault_with_links: Path, capsys: pytest.CaptureFixture
    ) -> None:
        results = _compute_backlinks(vault_with_links, "note-a")
        _display_backlinks(results, "note-a", vault_with_links, json_output=True)
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert isinstance(data, list)
        names = {d["name"] for d in data}
        assert "note-b" in names
        assert "note-d" in names

    def test_no_results(
        self, vault_with_links: Path, capsys: pytest.CaptureFixture
    ) -> None:
        _display_backlinks([], "note-x", vault_with_links)
        captured = capsys.readouterr()
        assert "No backlinks found" in captured.out


# ---------------------------------------------------------------------------
#  _open_in_obsidian
# ---------------------------------------------------------------------------


class TestOpenInObsidian:
    def test_constructs_correct_uri(
        self, vault: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from notekey.markdown import Markdown

        calls: list[list[str]] = []

        def fake_run(cmd: list[str], **kwargs: object) -> None:
            calls.append(cmd)

        monkeypatch.setattr("subprocess.run", fake_run)

        md = Markdown(vault / "flask-app.md")
        uri = _open_in_obsidian(vault, md)
        assert "obsidian://open?vault=" in uri
        assert "file=flask-app.md" in uri
        assert len(calls) == 1
        assert calls[0] == ["open", uri]


# ---------------------------------------------------------------------------
#  _compute_stats / _display_stats
# ---------------------------------------------------------------------------


class TestComputeStats:
    def test_computes_stats(self, vault: Path) -> None:
        stats = _compute_stats(vault)
        assert stats["total_notes"] == 5
        assert stats["total_unique_tags"] >= 5
        assert stats["total_size_bytes"] > 0
        assert stats["total_words"] > 0
        assert stats["newest"] is not None
        assert stats["oldest"] is not None
        assert len(stats["top_tags"]) > 0

    def test_empty_vault(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        stats = _compute_stats(root)
        assert stats["total_notes"] == 0
        assert stats["total_unique_tags"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["newest"] is None


class TestDisplayStats:
    def test_with_data(self, vault: Path, capsys: pytest.CaptureFixture) -> None:
        stats = _compute_stats(vault)
        _display_stats(stats, vault)
        captured = capsys.readouterr()
        assert "Total notes:" in captured.out
        assert "5" in captured.out

    def test_json_output(self, vault: Path, capsys: pytest.CaptureFixture) -> None:
        stats = _compute_stats(vault)
        _display_stats(stats, vault, json_output=True)
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert data["total_notes"] == 5
        assert isinstance(data["top_tags"], list)

    def test_empty(self, capsys: pytest.CaptureFixture) -> None:
        _display_stats(
            {
                "total_notes": 0,
                "total_unique_tags": 0,
                "total_size_bytes": 0,
                "total_words": 0,
                "newest": None,
                "oldest": None,
                "top_tags": [],
            },
            Path.cwd(),
        )
        captured = capsys.readouterr()
        assert "No notes found" in captured.out

    def test_json_empty(self, capsys: pytest.CaptureFixture) -> None:
        _display_stats(
            {
                "total_notes": 0,
                "total_unique_tags": 0,
                "total_size_bytes": 0,
                "total_words": 0,
                "newest": None,
                "oldest": None,
                "top_tags": [],
            },
            Path.cwd(),
            json_output=True,
        )
        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert data["total_notes"] == 0


# ---------------------------------------------------------------------------
#  main() — new subcommands
# ---------------------------------------------------------------------------


class TestMainNewSubcommands:
    def test_main_tags(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "tags"])

        main()

        captured = capsys.readouterr()
        assert "python" in captured.out
        assert "unique tags" in captured.out

    def test_main_tags_json(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "tags", "--json"])

        main()

        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert isinstance(data, list)

    def test_main_backlinks(
        self,
        vault_with_links: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault_with_links))
        monkeypatch.setattr(sys, "argv", ["notekey", "backlinks", "note-a"])

        main()

        captured = capsys.readouterr()
        assert "note-b" in captured.out
        assert "note-d" in captured.out

    def test_main_backlinks_json(
        self,
        vault_with_links: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault_with_links))
        monkeypatch.setattr(sys, "argv", ["notekey", "backlinks", "note-a", "--json"])

        main()

        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert isinstance(data, list)
        names = {d["name"] for d in data}
        assert "note-b" in names

    def test_main_backlinks_not_found(
        self,
        vault_with_links: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault_with_links))
        monkeypatch.setattr(sys, "argv", ["notekey", "backlinks", "missing"])

        main()

        captured = capsys.readouterr()
        assert "No note found" in captured.out

    def test_main_open(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "open", "=flask-app"])
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)

        main()

        captured = capsys.readouterr()
        assert "Opened:" in captured.out
        assert "obsidian://" in captured.out

    def test_main_open_not_found(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "open", "missing"])

        main()

        captured = capsys.readouterr()
        assert "No file found matching" in captured.out

    def test_main_open_multiple_matches(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "open", "a"])
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)

        main()

        captured = capsys.readouterr()
        assert "Multiple matches" in captured.out

    def test_main_stats(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "stats"])

        main()

        captured = capsys.readouterr()
        assert "Total notes:" in captured.out
        assert "5" in captured.out

    def test_main_stats_json(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "stats", "--json"])

        main()

        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert data["total_notes"] == 5

    def test_main_search_json(
        self,
        vault: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        monkeypatch.setenv("OBSIDIAN_VAULT", str(vault))
        monkeypatch.setattr(sys, "argv", ["notekey", "search", "--json"])

        main()

        captured = capsys.readouterr()
        import json

        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) == 5


# ---------------------------------------------------------------------------
#  build_parser — new subcommands
# ---------------------------------------------------------------------------


class TestBuildParserNewSubcommands:
    def test_tags_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["tags"])
        assert args.command == "tags"
        assert not args.json

    def test_tags_json_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["tags", "--json"])
        assert args.json is True

    def test_backlinks_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["backlinks", "my-note"])
        assert args.command == "backlinks"
        assert args.filename == "my-note"

    def test_backlinks_json_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["backlinks", "note", "--json"])
        assert args.json is True

    def test_open_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["open", "my-note"])
        assert args.command == "open"
        assert args.filename == "my-note"

    def test_stats_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["stats"])
        assert args.command == "stats"
        assert not args.json

    def test_stats_json_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["stats", "--json"])
        assert args.json is True

    def test_search_json_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["search", "--json"])
        assert args.json is True

    def test_version_short_flag(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["-v"])

    def test_version_long_flag(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])
