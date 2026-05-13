import argparse
import json
import os
import subprocess
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from urllib.parse import quote

from notekey.markdown import Markdown, Section
from notekey.template import BASE_FILTER_TEMPLATE, MOC_TEMPLATE
from notekey.utils import normalize_size


# ---------------------------------------------------------------------------
#  Path helpers
# ---------------------------------------------------------------------------


def _resolve_path(path: str | None = None) -> str:
    """Return the effective path: CLI arg > ``$OBSIDIAN_VAULT`` > ``.``."""
    if path is not None:
        return path
    env = os.environ.get("OBSIDIAN_VAULT")
    if env:
        return env
    return "."


def _get_folder(path: str | None = None) -> Path:
    target = Path(path).expanduser().resolve() if path else Path.cwd()

    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {target}")

    return target


def _find_vault_root(target: Path) -> Path:
    for candidate in [target, *target.parents]:
        if (candidate / ".obsidian").is_dir():
            return candidate
    raise FileNotFoundError(f"No Obsidian vault (.obsidian) found above: {target}")


def _relative_to_vault(md: Markdown, vault_root: Path) -> str:
    """Return the file path relative to the vault root."""
    try:
        return md._path.relative_to(vault_root).as_posix()
    except ValueError:
        return md._path.name


# ---------------------------------------------------------------------------
#  Init helpers
# ---------------------------------------------------------------------------


def _build_filters(name: str, tags: str | None = None) -> str:
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else []

    filters: list[str] = []
    for tag in [name, *parsed_tags]:
        if tag and tag not in filters:
            filters.append(tag)

    return ", ".join(f'"{tag}"' for tag in filters)


def _create_base(
    target: Path, name: str, tags: str | None = None, force: bool = False
) -> Path:
    vault_root = _find_vault_root(target)
    folder = target.relative_to(vault_root).as_posix()
    filters = _build_filters(name, tags)
    base_path = target / f"{name}.base"
    content = BASE_FILTER_TEMPLATE.format(
        folder=folder, name=name, filters=filters
    ).lstrip()

    if base_path.exists() and not force:
        raise FileExistsError(f"Base file already exists: {base_path}")

    base_path.write_text(content, encoding="utf-8")
    return base_path


def _create_markdown(target: Path, name: str, force: bool = False) -> Path:
    markdown_path = target / f"{name}.md"
    content = MOC_TEMPLATE.format(name=name).lstrip()

    if markdown_path.exists() and not force:
        raise FileExistsError(f"Markdown file already exists: {markdown_path}")

    markdown_path.write_text(content, encoding="utf-8")
    return markdown_path


# ---------------------------------------------------------------------------
#  Search
# ---------------------------------------------------------------------------


def _parse_filter(value: str) -> tuple[bool, str]:
    """Parse a filter value into (exact_match, clean_value).

    ``"=python"`` → ``(True, "python")``  — exact match
    ``"python"``   → ``(False, "python")`` — substring / containment match
    ``"= hello"``  → ``(True, " hello")``  — spaces after ``=`` are preserved
    """
    if value.startswith("="):
        return True, value[1:]
    return False, value


def _filename_candidates(md_path: Path, vault_root: Path) -> tuple[str, str, str]:
    """Return filename candidates: stem, vault-relative path, vault-relative stem."""
    stem = md_path.stem
    try:
        rel = md_path.relative_to(vault_root)
        return stem, rel.as_posix(), rel.with_suffix("").as_posix()
    except ValueError:
        return stem, md_path.name, stem


def _search_files(
    vault_root: Path,
    tags: list[str] | None = None,
    filename: str | None = None,
    content: str | None = None,
) -> list[Markdown]:
    """Walk *vault_root* for ``.md`` files and return those matching.

    Filter values prefixed with ``=`` require an **exact** match;
    unprefixed values use substring / containment matching.
    """
    filename_exact, filename_val = (
        _parse_filter(filename) if filename else (False, None)
    )
    content_exact, content_val = _parse_filter(content) if content else (False, None)
    parsed_tags: list[tuple[bool, str]] = (
        [_parse_filter(t) for t in tags] if tags else []
    )

    results: list[Markdown] = []

    for md_path in sorted(vault_root.rglob("*.md")):
        # --- filename filter (cheapest) ---
        if filename_val is not None:
            candidates = _filename_candidates(md_path, vault_root)

            if filename_exact:
                if filename_val not in candidates:
                    continue
            else:
                val_lower = filename_val.lower()
                if not any(val_lower in candidate.lower() for candidate in candidates):
                    continue

        # --- content filter (raw text scan, no full parse yet) ---
        if content_val is not None:
            try:
                raw = md_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if content_exact:
                if content_val != raw:
                    continue
            else:
                if content_val.lower() not in raw.lower():
                    continue

        # --- tags filter (requires full parse — most expensive) ---
        try:
            md = Markdown(md_path)
        except Exception:
            continue

        if parsed_tags:
            md_tag_lower = [t.lower() for t in md.tags]
            matched = True
            for exact, user_tag in parsed_tags:
                if exact:
                    if not any(user_tag.lower() == ft.lower() for ft in md.tags):
                        matched = False
                        break
                else:
                    if not any(user_tag.lower() in ft for ft in md_tag_lower):
                        matched = False
                        break
            if not matched:
                continue

        results.append(md)

    return results


def _json_serializable(md: Markdown, vault_root: Path) -> dict:
    """Convert a ``Markdown`` object to a JSON-safe dictionary."""
    return {
        "name": md.name,
        "path": _relative_to_vault(md, vault_root),
        "tags": md.tags,
        "links": md.links,
        "reading_time": md.reading_time,
        "size": md._normalize_size(),
        "size_bytes": int(md._size_bytes),
        "created_at": md.created_at.isoformat(),
        "updated_at": md.updated_at.isoformat(),
        "title": md.metadata.get("title", ""),
    }


# ---------------------------------------------------------------------------
#  Display helpers
# ---------------------------------------------------------------------------


def _display_search_results(
    results: list[Markdown], vault_root: Path, json_output: bool = False
) -> None:
    """Print search results — table or JSON."""
    if json_output:
        data = [_json_serializable(md, vault_root) for md in results]
        print(json.dumps(data, indent=2))
        return

    if not results:
        print("No matching files found.")
        return

    print(f"\nFound {len(results)} file{'s' if len(results) != 1 else ''}:\n")

    name_width = max(len(_relative_to_vault(r, vault_root)) for r in results)
    name_width = max(name_width, 8) + 2

    for md in results:
        rel = _relative_to_vault(md, vault_root)
        tags_str = ", ".join(md.tags[:5]) + ("..." if len(md.tags) > 5 else "") or "—"
        print(
            f"  {rel:<{name_width}}  "
            f"tags: [{tags_str}]  "
            f"{md.reading_time}  "
            f"{md._normalize_size()}"
        )
    print()


def _display_file(md: Markdown, vault_root: Path) -> None:
    """Print the full raw content of a ``Markdown`` file."""
    print(md.content, end="")


def _section_outline(md: Markdown) -> list[tuple[int, Section]]:
    """Return 1-based section numbers paired with parsed sections."""
    return list(enumerate(md.sections, start=1))


def _section_json(
    md: Markdown,
    vault_root: Path,
    number: int,
    section: Section,
    content: str | None = None,
) -> dict:
    """Convert a section to a JSON-safe dictionary."""
    data = {
        "number": number,
        "title": section.title,
        "heading": section.heading,
        "line": section.index + 1,
        "path": _relative_to_vault(md, vault_root),
    }
    if content is not None:
        data["content"] = content
    return data


def _display_sections(
    md: Markdown, vault_root: Path, json_output: bool = False
) -> None:
    """Print a note's section outline."""
    outline = _section_outline(md)

    if json_output:
        print(
            json.dumps(
                {
                    "name": md.name,
                    "path": _relative_to_vault(md, vault_root),
                    "sections": [
                        _section_json(md, vault_root, number, section)
                        for number, section in outline
                    ],
                },
                indent=2,
            )
        )
        return

    rel_path = _relative_to_vault(md, vault_root)
    if not outline:
        print(f"No sections found in {rel_path}.")
        return

    print(f"{rel_path}\n")
    number_width = len(str(len(outline)))
    for number, section in outline:
        marker = "#" * section.heading
        print(f"  {number:>{number_width}}  {marker} {section.title}")


def _find_sections(md: Markdown, query: str) -> list[tuple[int, Section]]:
    """Find sections by 1-based number or case-insensitive title match."""
    outline = _section_outline(md)

    try:
        number = int(query)
    except ValueError:
        number = 0

    if 1 <= number <= len(outline):
        return [outline[number - 1]]

    exact, value = _parse_filter(query)
    value_lower = value.lower()
    if exact:
        return [
            (number, section)
            for number, section in outline
            if section.title.lower() == value_lower
        ]

    return [
        (number, section)
        for number, section in outline
        if value_lower in section.title.lower()
    ]


def _section_subtree_content(md: Markdown, selected: Section) -> str:
    """Return a section and nested subsections until the next peer/ancestor."""
    lines = md.content.splitlines()
    end = len(lines)

    for section in md.sections:
        if section.index <= selected.index:
            continue
        if section.heading <= selected.heading:
            end = section.index
            break

    return "\n".join(lines[selected.index : end]).rstrip("\n") + "\n"


def _display_section_match(
    md: Markdown,
    vault_root: Path,
    match: tuple[int, Section],
    json_output: bool = False,
) -> None:
    """Print a selected section as Markdown or JSON."""
    number, section = match
    content = _section_subtree_content(md, section)

    if json_output:
        print(
            json.dumps(
                _section_json(md, vault_root, number, section, content), indent=2
            )
        )
        return

    print(content, end="")


def _display_section_match_error(
    md: Markdown,
    vault_root: Path,
    query: str,
    matches: list[tuple[int, Section]],
) -> None:
    """Print a helpful message for missing or ambiguous section lookups."""
    if not matches:
        print(f"No section found matching: {query}")
        return

    print(f'Multiple sections match "{query}":\n')
    number_width = len(str(len(md.sections)))
    for number, section in matches:
        marker = "#" * section.heading
        print(f"  {number:>{number_width}}  {marker} {section.title}")
    print(
        f"\nUse --section NUMBER or a more specific title in {_relative_to_vault(md, vault_root)}."
    )


# ---------------------------------------------------------------------------
#  Tags
# ---------------------------------------------------------------------------


def _compute_tags(vault_root: Path) -> list[tuple[str, int]]:
    """Walk the vault and return (tag, count) sorted by frequency descending."""
    files = _search_files(vault_root)
    counter: Counter[str] = Counter()
    for md in files:
        for tag in md.tags:
            counter[tag] += 1
    return counter.most_common()


def _display_tags(tags: list[tuple[str, int]], json_output: bool = False) -> None:
    """Print tag index — table or JSON."""
    if json_output:
        data = [{"tag": t, "count": c} for t, c in tags]
        print(json.dumps(data, indent=2))
        return

    if not tags:
        print("No tags found in vault.")
        return

    print(f"\n{len(tags)} unique tags:\n")
    max_width = max(len(t) for t, _ in tags)
    for tag, count in tags:
        print(f"  {tag:<{max_width + 2}} {count}")
    print()


# ---------------------------------------------------------------------------
#  Backlinks
# ---------------------------------------------------------------------------


def _compute_backlinks(vault_root: Path, target: str) -> list[Markdown]:
    """Return notes whose links reference *target*."""
    target_note = _search_files(vault_root, filename=f"={target}")
    if not target_note:
        # Try substring match as fallback
        target_note = _search_files(vault_root, filename=target)

    if not target_note:
        raise FileNotFoundError(f"No note found matching: {target}")

    target_md = target_note[0]
    backlinked: list[Markdown] = []

    for md in _search_files(vault_root):
        if md.name == target_md.name:
            continue
        for link in md.links:
            if link == target_md.name or link.startswith(f"{target_md.name}|"):
                backlinked.append(md)
                break

    return backlinked


def _display_backlinks(
    results: list[Markdown],
    target: str,
    vault_root: Path,
    json_output: bool = False,
) -> None:
    """Print backlinks — table or JSON."""
    if json_output:
        data = [_json_serializable(md, vault_root) for md in results]
        print(json.dumps(data, indent=2))
        return

    if not results:
        print(f"No backlinks found for: {target}")
        return

    print(
        f"\n{len(results)} note{'s' if len(results) != 1 else ''} "
        f"linking to '{target}':\n"
    )
    _display_search_results(results, vault_root)


# ---------------------------------------------------------------------------
#  Open
# ---------------------------------------------------------------------------


def _open_in_obsidian(vault_root: Path, md: Markdown) -> str:
    """Open *md* in Obsidian and return the URI used."""
    vault_name = vault_root.name
    rel_path = _relative_to_vault(md, vault_root)
    uri = f"obsidian://open?vault={quote(vault_name)}&file={quote(rel_path)}"
    subprocess.run(["open", uri], check=False)
    return uri


# ---------------------------------------------------------------------------
#  Stats
# ---------------------------------------------------------------------------


def _compute_stats(vault_root: Path) -> dict:
    """Walk the vault and return aggregate statistics."""
    files = _search_files(vault_root)

    if not files:
        return {
            "total_notes": 0,
            "total_unique_tags": 0,
            "total_size_bytes": 0,
            "total_words": 0,
            "newest": None,
            "oldest": None,
            "top_tags": [],
        }

    total_size = sum(md._size_bytes for md in files)
    total_words = sum(len(md._body.split()) for md in files)

    all_tags: set[str] = set()
    tag_counter: Counter[str] = Counter()
    for md in files:
        all_tags.update(md.tags)
        for tag in md.tags:
            tag_counter[tag] += 1

    newest = max(files, key=lambda m: m.updated_at)
    oldest = min(files, key=lambda m: m.created_at)

    return {
        "total_notes": len(files),
        "total_unique_tags": len(all_tags),
        "total_size_bytes": int(total_size),
        "total_words": total_words,
        "newest": newest,
        "oldest": oldest,
        "top_tags": tag_counter.most_common(10),
    }


def _display_stats(stats: dict, vault_root: Path, json_output: bool = False) -> None:
    """Print vault stats — table or JSON."""
    if json_output:
        data = {
            "total_notes": stats["total_notes"],
            "total_unique_tags": stats["total_unique_tags"],
            "total_size_bytes": stats["total_size_bytes"],
            "total_size": normalize_size(stats["total_size_bytes"]),
            "total_words": stats["total_words"],
            "newest": (
                _relative_to_vault(stats["newest"], vault_root)
                if stats["newest"]
                else None
            ),
            "oldest": (
                _relative_to_vault(stats["oldest"], vault_root)
                if stats["oldest"]
                else None
            ),
            "top_tags": [{"tag": t, "count": c} for t, c in stats["top_tags"]],
        }
        print(json.dumps(data, indent=2))
        return

    if stats["total_notes"] == 0:
        print("No notes found in vault.")
        return

    print(f"\n  Total notes:         {stats['total_notes']}")
    print(f"  Unique tags:         {stats['total_unique_tags']}")
    print(f"  Total size:          {normalize_size(stats['total_size_bytes'])}")
    print(f"  Total words:         {stats['total_words']:,}")
    if stats["newest"]:
        print(
            f"  Newest note:         {_relative_to_vault(stats['newest'], vault_root)}"
        )
    if stats["oldest"]:
        print(
            f"  Oldest note:         {_relative_to_vault(stats['oldest'], vault_root)}"
        )
    if stats["top_tags"]:
        print(f"\n  Top tags:")
        max_width = max(len(t) for t, _ in stats["top_tags"])
        for tag, count in stats["top_tags"]:
            print(f"    {tag:<{max_width + 2}} {count}")
    print()


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notekey")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {version('notekey')}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- init ---------------------------------------------------------------
    init_parser = subparsers.add_parser("init", help="Initialize notekey in a folder")
    init_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Target folder (defaults to current directory)",
    )
    init_parser.add_argument(
        "-t",
        "--tags",
        help="Comma-separated tags to append to the default {name} filter in {name}.base",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing {name}.base and {name}.md files",
    )

    # -- search -------------------------------------------------------------
    search_parser = subparsers.add_parser(
        "search", help="Search markdown files in the vault"
    )
    search_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Directory to search in (defaults to $OBSIDIAN_VAULT or current directory)",
    )
    search_parser.add_argument(
        "-t",
        "--tags",
        help="Comma-separated list of tags — file must have ALL of them",
    )
    search_parser.add_argument(
        "-f",
        "--filename",
        help="Substring to match in the filename (case-insensitive)",
    )
    search_parser.add_argument(
        "-c",
        "--content",
        help="Substring to match in the file content (case-insensitive)",
    )
    search_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    # -- read ---------------------------------------------------------------
    read_parser = subparsers.add_parser(
        "read", help="Read a single markdown file by name or path"
    )
    read_parser.add_argument(
        "filename",
        help="Filename or path to match — first match wins (prefix = for exact)",
    )
    read_group = read_parser.add_mutually_exclusive_group()
    read_group.add_argument(
        "--sections",
        action="store_true",
        help="List available Markdown headings in the matched note",
    )
    read_group.add_argument(
        "--section",
        help="Read a heading subtree by 1-based section number or title match",
    )
    read_parser.add_argument(
        "--json",
        action="store_true",
        help="Output section discovery or selected section as JSON",
    )

    # -- tags ---------------------------------------------------------------
    tags_parser = subparsers.add_parser("tags", help="List all unique tags with counts")
    tags_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    # -- backlinks ----------------------------------------------------------
    backlinks_parser = subparsers.add_parser(
        "backlinks", help="Show notes linking to a target note"
    )
    backlinks_parser.add_argument(
        "filename",
        help="Target note name or path to find backlinks for",
    )
    backlinks_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    # -- open ---------------------------------------------------------------
    open_parser = subparsers.add_parser("open", help="Open a note in Obsidian")
    open_parser.add_argument(
        "filename",
        help="Filename or path to match — first match wins",
    )

    # -- stats --------------------------------------------------------------
    stats_parser = subparsers.add_parser("stats", help="Show vault-wide statistics")
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        target = _get_folder(args.path)
        current_location = str(target)
        folder_name = target.name
        base_path = _create_base(target, folder_name, tags=args.tags, force=args.force)
        markdown_path = _create_markdown(target, folder_name, force=args.force)

        print(f"Full path: {current_location}")
        print(f"Folder name: {folder_name}")
        print(f"Created base: {base_path}")
        print(f"Created markdown: {markdown_path}")

    elif args.command == "search":
        target = _get_folder(_resolve_path(args.path))
        vault_root = _find_vault_root(target)
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else None
        results = _search_files(
            vault_root,
            tags=tags,
            filename=args.filename,
            content=args.content,
        )
        _display_search_results(results, vault_root, json_output=args.json)

    elif args.command == "read":
        target = _get_folder(_resolve_path())
        vault_root = _find_vault_root(target)
        results = _search_files(vault_root, filename=args.filename)

        if not results:
            print(f"No file found matching: {args.filename}")
            return

        md = results[0]
        if len(results) > 1 and not args.json:
            print(f"Multiple matches — showing first of {len(results)}:")

        if args.sections:
            _display_sections(md, vault_root, json_output=args.json)
        elif args.section:
            matches = _find_sections(md, args.section)
            if len(matches) == 1:
                _display_section_match(
                    md, vault_root, matches[0], json_output=args.json
                )
            else:
                _display_section_match_error(md, vault_root, args.section, matches)
        else:
            _display_file(md, vault_root)

    elif args.command == "tags":
        target = _get_folder(_resolve_path())
        vault_root = _find_vault_root(target)
        tags_list = _compute_tags(vault_root)
        _display_tags(tags_list, json_output=args.json)

    elif args.command == "backlinks":
        target = _get_folder(_resolve_path())
        vault_root = _find_vault_root(target)
        try:
            results = _compute_backlinks(vault_root, args.filename)
        except FileNotFoundError as e:
            print(str(e))
            return
        _display_backlinks(results, args.filename, vault_root, json_output=args.json)

    elif args.command == "open":
        target = _get_folder(_resolve_path())
        vault_root = _find_vault_root(target)
        results = _search_files(vault_root, filename=args.filename)

        if not results:
            print(f"No file found matching: {args.filename}")
        else:
            if len(results) > 1:
                print(
                    f"Multiple matches — opening first of {len(results)}: "
                    f"{_relative_to_vault(results[0], vault_root)}"
                )
            uri = _open_in_obsidian(vault_root, results[0])
            print(f"Opened: {uri}")

    elif args.command == "stats":
        target = _get_folder(_resolve_path())
        vault_root = _find_vault_root(target)
        stats = _compute_stats(vault_root)
        _display_stats(stats, vault_root, json_output=args.json)


if __name__ == "__main__":
    main()
