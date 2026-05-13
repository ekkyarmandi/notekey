# notekey

CLI utilities for working with Markdown notes in an Obsidian vault.

`notekey` can:

- initialize a folder with an Obsidian `.base` file and a matching Markdown note
- search vault notes by tag, filename, or content
- read a single note, discover its headings, or read a specific heading section

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
notekey read FILENAME [--sections | --section SECTION] [--json]
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

### Read a note or section

```bash
notekey read flask-app
```

For an exact filename match:

```bash
notekey read "=flask-app"
```

List the headings in a note before choosing a section:

```bash
notekey read flask-app --sections
```

Example output:

```text
flask-app.md

  1  # Flask App
  2  ## Setup
  3  ## Open Questions
  4  ### API Shape
```

Read a section by its 1-based outline number:

```bash
notekey read flask-app --section 3
```

Read a section by a case-insensitive title substring:

```bash
notekey read flask-app --section api
```

Section reads include the selected heading and its nested child headings, stopping at the next heading of the same or higher level. If a title search matches multiple headings, `notekey` prints the matching outline entries so you can retry with a number or a more specific title.

For exact section title matching, prefix the section query with `=`:

```bash
notekey read flask-app --section "=API Shape"
```

Section discovery and section reads can return JSON:

```bash
notekey read flask-app --sections --json
notekey read flask-app --section 4 --json
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
