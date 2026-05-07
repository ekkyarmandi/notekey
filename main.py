import argparse
from pathlib import Path

from template import BASE_FILTER_TEMPLATE, MOC_TEMPLATE


def _get_folder(path: str | None = None) -> Path:
    target = Path(path).expanduser().resolve() if path else Path.cwd()

    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")
    if not target.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {target}")

    return target


def _build_filters(name: str, tags: str | None = None) -> str:
    parsed_tags = [tag.strip() for tag in tags.split(",")] if tags else []

    filters: list[str] = []
    for tag in [name, *parsed_tags]:
        if tag and tag not in filters:
            filters.append(tag)

    return ", ".join(f'"{tag}"' for tag in filters)


def _create_base(target: Path, name: str, tags: str | None = None, force: bool = False) -> Path:
    folder = target.name
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



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notekey")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize notekey in a folder")
    init_parser.add_argument(
        "path",
        nargs="?",
        default=".",
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


if __name__ == "__main__":
    main()
