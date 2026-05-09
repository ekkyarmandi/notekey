# notekey

CLI utilities for working with Markdown notes in an Obsidian vault.

`notekey` can:

- initialize a folder with an Obsidian `.base` file and a matching Markdown note
- search vault notes by tag, filename, or content
- read a single note by filename or path match

## Requirements

- Python 3.11+
- An Obsidian vault directory containing a `.obsidian/` folder

## Installation

After the package is published to PyPI:

```bash
pip install notekey
```

## Usage

```bash
notekey init [path]
notekey search [path] [--tags TAGS] [--filename NAME] [--content TEXT]
notekey read FILENAME
```

For `init`, omitting `path` uses the current directory.

For `search` and `read`, omitting `path` uses the `OBSIDIAN_VAULT` environment variable. If that variable is not set, it uses the current directory.

```bash
export OBSIDIAN_VAULT="/path/to/your/vault"
```

### Initialize a note folder

```bash
cd /path/to/vault/Projects/MyProject
notekey init
```

Or pass the target folder explicitly:

```bash
notekey init /path/to/vault/Projects/MyProject
```

This creates:

- `MyProject.base`
- `MyProject.md`

Add extra base filters with comma-separated tags:

```bash
notekey init /path/to/vault/Projects/MyProject --tags python,docs
```

Overwrite existing generated files with:

```bash
notekey init /path/to/vault/Projects/MyProject --force
```

### Search notes

Search by tag:

```bash
notekey search --tags python
```

Search by multiple tags. Files must match all tags:

```bash
notekey search --tags python,web
```

Search by filename:

```bash
notekey search --filename flask
```

Search by content:

```bash
notekey search --content pandas
```

Use `=` for exact matches:

```bash
notekey search --tags "=python"
notekey search --filename "=deep/hidden-note"
```

### Read a note

```bash
notekey read flask-app
```

For an exact filename match:

```bash
notekey read "=flask-app"
```

## Development

Run tests with:

```bash
pytest
```

Build distribution files with:

```bash
python -m build
```

Upload is intentionally manual. Use TestPyPI or PyPI with your API token when ready.
