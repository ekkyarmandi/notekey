import argparse
import os
from pathlib import Path

from notekey.markdown import Markdown
from notekey.template import BASE_FILTER_TEMPLATE, MOC_TEMPLATE


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


def _build_filters(name: str, tags: str | None = None) -> str:
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else []

    filters: list[str] = []
    for tag in [name, *parsed_tags]:
        if tag and tag not in filters:
            filters.append(tag)

    return ", ".join(f'"{tag}"' for tag in filters)


def _create_base(target: Path, name: str, tags: str | None = None, force: bool = False) -> Path:
    vault_root = _find_vault_root(target)
    folder = target.relative_to(vault_root).as_posix()
    filters = _build_filters(name, tags)
    base_path = target / f"{name}.base"
    content = BASE_FILTER_TEMPLATE.format(folder=folder, name=name, filters=filters).lstrip()

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

    Examples::

        --tags py          # tag contains "py" (matches "python")
        --tags "=python"   # tag equals "python"
        --filename test    # filename contains "test"
        --filename "=test" # filename equals "test"

    Filters are applied cheapest-first:
      1. Filename (no parsing needed)
      2. Content  (raw text scan)
      3. Tags     (requires full ``Markdown`` object)
    """
    # Parse exact/substring flags upfront.
    filename_exact, filename_val = (
        _parse_filter(filename) if filename else (False, None)
    )
    content_exact, content_val = (
        _parse_filter(content) if content else (False, None)
    )
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


def _display_search_results(results: list[Markdown], vault_root: Path) -> None:
    """Print search results with paths relative to the vault root."""
    if not results:
        print("No matching files found.")
        return

    print(f"\nFound {len(results)} file{'s' if len(results) != 1 else ''}:\n")

    # Column widths
    name_width = max(len(_relative_to_vault(r, vault_root)) for r in results)
    name_width = max(name_width, 8) + 2  ##### ≥ "Filename"

    for md in results:
        rel = _relative_to_vault(md, vault_root)
        tags_str = (
            ", ".join(md.tags[:5])
            + ("..." if len(md.tags) > 5 else "")
            or "—"
        )
        print(
            f"  {rel:<{name_width}}  "
            f"tags: [{tags_str}]  "
            f"{md.reading_time}  "
            f"{md._normalize_size()}"
        )
    print()


def _relative_to_vault(md: Markdown, vault_root: Path) -> str:
    """Return the file path relative to the vault root."""
    try:
        return md._path.relative_to(vault_root).as_posix()
    except ValueError:
        return md._path.name


def _display_file(md: Markdown, vault_root: Path) -> None:
    """Print the full raw content of a ``Markdown`` file."""
    print(md.content, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notekey")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- init ---------------------------------------------------------------
    init_parser = subparsers.add_parser("init", help="Initialize notekey in a folder")
    init_parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Target folder (defaults to $OBSIDIAN_VAULT or current directory)",
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
    search_parser = subparsers.add_parser("search", help="Search markdown files in the vault")
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

    # -- read ---------------------------------------------------------------
    read_parser = subparsers.add_parser("read", help="Read a single markdown file by name or path")
    read_parser.add_argument(
        "filename",
        help="Filename or path to match — first match wins (prefix = for exact)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "init":
        target = _get_folder(_resolve_path(args.path))
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
        _display_search_results(results, vault_root)

    elif args.command == "read":
        target = _get_folder(_resolve_path())
        vault_root = _find_vault_root(target)
        results = _search_files(vault_root, filename=args.filename)

        if not results:
            print(f"No file found matching: {args.filename}")
        elif len(results) > 1:
            print(f"Multiple matches — showing first of {len(results)}:")
            _display_file(results[0], vault_root)
        else:
            _display_file(results[0], vault_root)


if __name__ == "__main__":
    main()
