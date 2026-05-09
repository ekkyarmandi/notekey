<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# do me some research about a Python library that is able to turn a Markdown file into an object, treat the frontmatter as an attribute, and extract important properties like attribute, file_size, length, or number of characters,  reading approximately in minutes?

I have enough info to provide a comprehensive answer. Here's the full picture:

***

## Best Python Libraries for Markdown → Object with Frontmatter + Metrics

No single library does everything out of the box, but the **best combo is `python-frontmatter` + `readtime`**, optionally paired with `mrkdwn_analysis` for deeper stats. Here's a breakdown:

***

## `python-frontmatter` — Core Library

The go-to library for turning a Markdown file into a Python `Post` object. Install via:[^1_1][^1_2]

```bash
pip install python-frontmatter
```

The `Post` object treats every frontmatter key as a dict-accessible attribute:[^1_2][^1_3]

```python
import frontmatter

post = frontmatter.load("article.md")

# Frontmatter as attributes
print(post["title"])        # from ---title: ...---
print(post["date"])
print(post.metadata)        # full frontmatter dict
print(post.keys())          # list of frontmatter keys

# Body content
print(post.content)         # markdown body (sans frontmatter)
```

It supports YAML (default), JSON, and TOML frontmatter, and you can write back with `frontmatter.dump()`. Supports `load()` from filename or file-like object, and `loads()` from a raw string.[^1_4][^1_2]

***

## `readtime` — Reading Time

The `readtime` library calculates reading time based on **Medium's formula (~265 WPM)** and works natively with plain text, HTML, or Markdown:[^1_5][^1_6]

```bash
pip install readtime
```

```python
import readtime

result = readtime.of_markdown(post.content)
print(result.text)     # e.g. "3 min read"
print(result.seconds)  # total seconds
```

You can also customize WPM with `readtime.of_text(text, wpm=200)`.[^1_5]

***

## `markdown-readtime` — Richer Reading Metrics

A newer alternative (`pip install markdown-readtime`) with more granular control, including emoji processing, image time, and code block time:[^1_7]

```python
from markdown_readtime import estimate, minutes, words

read_time = estimate(post.content)
print(read_time.total_seconds)
print(read_time.word_count)
print(read_time.formatted)  # "3 min read"
```

Supports customizable `ReadSpeed(wpm, seconds_per_image, seconds_per_code_block, ...)` config.[^1_7]

***

## `mrkdwn_analysis` — Deep File Analysis

For file-level stats (character count, word count, structural parsing), use `mrkdwn_analysis`:[^1_8]

```bash
pip install mrkdwn_analysis
```

```python
from mrkdwn_analysis import MarkdownAnalyzer

analyzer = MarkdownAnalyzer("article.md")
print(analyzer.count_words())       # word count
print(analyzer.count_characters())  # char count (excl. spaces)
print(analyzer.identify_headers())  # all H1–H6 headers
print(analyzer.identify_links())    # all links
```

It does **not** parse frontmatter — best used alongside `python-frontmatter`.[^1_8]

***

## Putting It All Together

Here's a complete recipe combining all three capabilities:

```python
import os
import frontmatter
import readtime
from mrkdwn_analysis import MarkdownAnalyzer

file_path = "article.md"

# Load as object with frontmatter as attributes
post = frontmatter.load(file_path)

# File-level properties (using os/pathlib)
file_size = os.path.getsize(file_path)  # bytes
char_count = len(post.content)
word_count = len(post.content.split())

# Reading time
rt = readtime.of_markdown(post.content)

print({
    "title":        post["title"],          # frontmatter attr
    "date":         post["date"],           # frontmatter attr
    "file_size":    f"{file_size} bytes",
    "char_count":   char_count,
    "word_count":   word_count,
    "reading_time": rt.text,               # "3 min read"
    "read_seconds": rt.seconds,
})
```


***

## Quick Library Comparison

| Library | Frontmatter → Object | Reading Time | Word/Char Count | Structural Parse |
| :-- | :-- | :-- | :-- | :-- |
| `python-frontmatter` [^1_1][^1_2] | ✅ Native `Post` obj | ❌ | Manual via `len()` | ❌ |
| `readtime` [^1_5][^1_6] | ❌ | ✅ Medium formula | ❌ | ❌ |
| `markdown-readtime` [^1_7] | ❌ | ✅ More granular | ✅ `word_count` | ❌ |
| `mrkdwn_analysis` [^1_8] | ❌ | ❌ | ✅ Words + chars | ✅ Headers, links, lists |

For file size, use `os.path.getsize()` or `pathlib.Path.stat().st_size` since no library exposes it directly as an attribute. `python-frontmatter` is the only one that truly models the Markdown file as a rich Python object with frontmatter as accessible attributes.[^1_9][^1_3][^1_2]
<span style="display:none">[^1_10][^1_11][^1_12][^1_13][^1_14][^1_15][^1_16][^1_17][^1_18][^1_19][^1_20][^1_21][^1_22][^1_23][^1_24][^1_25][^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_38][^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45][^1_46][^1_47][^1_48][^1_49][^1_50][^1_51][^1_52][^1_53][^1_54][^1_55][^1_56]</span>

<div align="center">⁂</div>

[^1_1]: https://github.com/eyeseast/python-frontmatter

[^1_2]: https://pypi.org/project/python-frontmatter/

[^1_3]: https://python-frontmatter.readthedocs.io/_/downloads/en/latest/pdf/

[^1_4]: https://python-frontmatter.readthedocs.io/en/latest/api.html

[^1_5]: https://pypi.org/project/readtime/

[^1_6]: https://pypi.org/project/readtime/1.0.4/

[^1_7]: https://libraries.io/pypi/markdown-readtime

[^1_8]: https://pypi.org/project/markdown-analysis/0.0.4/

[^1_9]: https://realpython.com/python-pathlib/

[^1_10]: https://blog.pesky.moe/posts/2024-07-23-python-frontmatter/

[^1_11]: https://pypi.org/project/pymd-frontmatter/

[^1_12]: https://gist.github.com/maxdemaio/9963fd7a68f6fac3c18c22d83a2a3048

[^1_13]: https://www.dennisokeeffe.com/blog/2021-07-23-frontmatter-parsing-with-python

[^1_14]: https://clawdchat.ai/post/60b56c79-f4b8-4e5c-afa7-856a8acc29c5

[^1_15]: https://florian-dahlitz.de/articles/calculate-the-estimated-reading-time-for-your-posts

[^1_16]: https://dev.to/okeeffed/frontmatter-parsing-with-python-5df4

[^1_17]: https://cran.r-project.org/web/packages/frontmatter/frontmatter.pdf

[^1_18]: https://stackoverflow.com/questions/43762694/how-to-add-post-content-reading-time-in-a-django-blog

[^1_19]: https://www.honeybadger.io/blog/python-markdown/

[^1_20]: https://www.lesinskis.com/markdown_in_python.html

[^1_21]: https://pypi.org/project/Markdownipy/

[^1_22]: https://safjan.com/python-packages-yaml-front-matter-markdown/

[^1_23]: https://markdown-it-py.readthedocs.io/en/latest/using.html

[^1_24]: https://github.com/chrisjsewell/markdown-it-pyrs

[^1_25]: https://pypi.org/project/markdown-it-py/

[^1_26]: https://stackoverflow.com/questions/47881611/efficient-way-of-reading-word-count-from-a-file-and-calculating-average-per-sent

[^1_27]: https://spidernote.wordpress.com/2021/10/04/markdown-it-py-notes/

[^1_28]: https://github.com/squidfunk/mkdocs-material/discussions/4999

[^1_29]: https://pypi.org/project/frontmatter/

[^1_30]: https://markdown-it-py.readthedocs.io

[^1_31]: https://www.facebook.com/groups/6430500355/posts/10159987613005356/

[^1_32]: https://stackoverflow.com/questions/14325654/how-to-use-python-markdown-to-process-a-file-that-is-read-in

[^1_33]: https://pypi.org/project/marko/0.5.1/

[^1_34]: https://forum.obsidian.md/t/what-implementation-of-time-based-workflow-is-to-be-followed-system-mtime-or-date-modified-frontmatter-values/101610

[^1_35]: https://rstudio.github.io/reticulate/articles/r_markdown.html

[^1_36]: https://pypi.org/project/marko/0.6.0/

[^1_37]: https://pypi.org/project/obsidianmd-parser/

[^1_38]: https://pypi.org/project/grayskull/

[^1_39]: https://marko-py.readthedocs.io/en/latest/api.html

[^1_40]: https://blog.dennisokeeffe.com/blog/2021-07-23-frontmatter-parsing-with-python

[^1_41]: https://github.com/conda/grayskull/issues/564

[^1_42]: https://github.com/frostming/marko

[^1_43]: https://rich.readthedocs.io/en/latest/markdown.html

[^1_44]: https://marko-py.readthedocs.io/en/latest/extensions.html

[^1_45]: https://github.com/mfarragher/obsidiantools

[^1_46]: https://pypi.org/project/obsidian-metadata/

[^1_47]: https://dev.to/allen_yang_f905170c5a197b/how-to-convert-markdown-to-word-documents-using-python-1alj

[^1_48]: https://github.com/mfarragher/obsidiantools/blob/main/README.md

[^1_49]: https://github.com/gandreadis/markdown-word-count

[^1_50]: https://news.ycombinator.com/item?id=28525606

[^1_51]: https://pypi.org/project/mkdocs-timetoread-plugin/

[^1_52]: https://forum.obsidian.md/t/obsidiantools-python-package-for-doing-advanced-analytics-of-your-vault/24122

[^1_53]: https://stackoverflow.com/questions/36001482/read-doc-file-with-python

[^1_54]: https://stackoverflow.com/questions/58167526/how-do-i-set-up-a-simple-read-time-in-python

[^1_55]: https://github.com/johansan/ObsidianToHtml

[^1_56]: https://aeturrell.github.io/python4DS/markdown.html


---

# I would like you to go deep deeper about each library and told me which other functions they have

Here's a deep dive into all four libraries:

***

## `python-frontmatter`

The heart of the stack — converts any Markdown file into a `Post` object.[^2_1][^2_2]

### Reading Functions

| Function | Description |
| :-- | :-- |
| `frontmatter.load(fd)` | Load from filename or file-like object → returns `Post` |
| `frontmatter.loads(text)` | Load from a raw string → returns `Post` |
| `frontmatter.parse(text)` | Returns `(metadata_dict, content)` tuple — no full `Post` |
| `frontmatter.check(fd)` | Returns `True`/`False` if a file has frontmatter |
| `frontmatter.checks(text)` | Same as above but from raw string |

### Writing Functions

| Function | Description |
| :-- | :-- |
| `frontmatter.dump(post, fd)` | Serialize `Post` → write to file |
| `frontmatter.dumps(post)` | Serialize `Post` → return as string |

### `Post` Object Methods

| Method | Description |
| :-- | :-- |
| `post.content` | The markdown body (without frontmatter) |
| `post.metadata` | Full frontmatter as a `dict` |
| `post["key"]` | Access any frontmatter key directly |
| `post["key"] = val` | Set/add a frontmatter key |
| `del post["key"]` | Delete a frontmatter key |
| `post.get(key, default)` | Safe access with fallback |
| `post.keys()` | All frontmatter keys |
| `post.values()` | All frontmatter values |
| `post.to_dict()` | Full post as a serializable dict |

### Handlers (Frontmatter Formats)

Three built-in handlers for different frontmatter types:[^2_1]

- `YAMLHandler` — default (`---`-delimited)
- `JSONHandler` — JSON-style frontmatter
- `TOMLHandler` — TOML-style (`+++`-delimited)

Each handler implements `detect()`, `split()`, `load()`, `export()`, and `format()` — making it easy to create custom handlers.[^2_1]

***

## `readtime`

Implements Medium's exact read time algorithm: `seconds = num_words / 265 * 60 + img_weight * num_images`.[^2_3]

### Input Functions

| Function | Input Type |
| :-- | :-- |
| `readtime.of_text(text, wpm=265)` | Plain text |
| `readtime.of_markdown(text, wpm=265)` | Markdown (strips syntax before counting) |
| `readtime.of_html(text, wpm=265)` | HTML (strips tags before counting) |

### Result Object Properties

| Property | Description |
| :-- | :-- |
| `result.seconds` | Total reading time in seconds |
| `result.text` | Human-readable e.g. `"3 min"` |
| `str(result)` | `"3 min read"` — works as string directly |
| `result.wpm` | The WPM value used in calculation |

The `wpm` parameter is customizable:[^2_3]

```python
result = readtime.of_text(content, wpm=200)  # slower reader
```

Image weighting follows Medium's formula — `img_weight` starts at 12s and decreases by 1s per image, bottoming out at 3s.[^2_4][^2_3]

***

## `markdown-readtime`

A more granular alternative with multi-language and content-type-aware support.[^2_5]

### Functions

| Function | Description |
| :-- | :-- |
| `estimate(markdown)` | Estimate with default speed → `ReadTime` |
| `estimate_with_speed(markdown, speed)` | Estimate with custom `ReadSpeed` config |
| `minutes(markdown)` | Returns reading time as `int` minutes (rounded up) |
| `words(markdown)` | Returns word count as `int` |
| `formatted(markdown)` | Returns `"X min read"` string directly |

### `ReadTime` Result Object

| Property | Description |
| :-- | :-- |
| `total_seconds` | Total reading time in seconds |
| `formatted` | Human-readable string e.g. `"3 min read"` |
| `word_count` | Word count of the content |
| `image_count` | Number of images detected |
| `code_block_count` | Number of code blocks detected |

### `ReadSpeed` Configuration

```python
from markdown_readtime import ReadSpeed
speed = ReadSpeed(
    words_per_minute=200,        # default 200
    seconds_per_image=15,        # extra time per image
    seconds_per_code_block=25,   # extra time per code block
    count_emoji=True,            # count emojis as words
    chinese=False                # CJK character mode
)
```

Unlike `readtime`, it also counts **code blocks** and **emojis** as reading time contributors, making it more accurate for technical content.[^2_5]

***

## `mrkdwn_analysis`

The most structural of the four — parses and counts individual Markdown elements.[^2_6]

### All Methods on `MarkdownAnalyzer`

| Method | Returns | Description |
| :-- | :-- | :-- |
| `identify_headers()` | `dict` | All H1–H6 headers |
| `identify_sections()` | `dict` | Sections defined by `===` or `---` underlines |
| `identify_paragraphs()` | `dict` | All plain text paragraphs |
| `identify_blockquotes()` | `dict` | All `>` blockquote blocks |
| `identify_code_blocks()` | `dict` | All ``````` fenced code blocks |
| `identify_ordered_lists()` | `dict` | All `1. 2. 3.` ordered lists |
| `identify_unordered_lists()` | `dict` | All `- * +` unordered lists |
| `identify_tables()` | `dict` | All pipe-delimited tables |
| `identify_links()` | `dict` | Text links + image links separately |
| `check_links()` | `list` | Validates each URL — flags 404s |
| `identify_todos()` | `list` | All `- [ ]` todo items with line numbers |
| `count_elements(element_type)` | `int` | Count of any element type by name |
| `count_words()` | `int` | Total word count |
| `count_characters()` | `int` | Total characters (excluding spaces) |

The `check_links()` method actually **makes HTTP requests** to validate each found URL, which is unique among these libraries . It returns each broken link with its line number, link text, and URL.

***

## How They Complement Each Other

```python
import os, frontmatter, readtime
from markdown_readtime import estimate_with_speed, ReadSpeed
from mrkdwn_analysis import MarkdownAnalyzer

path = "post.md"
post = frontmatter.load(path)          # frontmatter as object
rt = readtime.of_markdown(post.content)  # reading time (Medium algo)

# detailed stats
analyzer = MarkdownAnalyzer(path)
speed = ReadSpeed(200, 12, 20, True, False)
rt2 = estimate_with_speed(post.content, speed)  # richer reading time

print({
    # frontmatter attrs
    **post.metadata,
    # file metrics
    "file_size_bytes": os.path.getsize(path),
    "char_count": analyzer.count_characters(),
    "word_count": analyzer.count_words(),
    # reading time
    "read_time": rt.text,
    "read_seconds": rt.seconds,
    "code_blocks": rt2.code_block_count,
    "image_count": rt2.image_count,
    # structure
    "headers": analyzer.identify_headers(),
    "todos": analyzer.identify_todos(),
    "broken_links": analyzer.check_links(),
})
```

This gives you a fully enriched document object with frontmatter as attributes, file-level metrics, structural analysis, and reading time — all from four lightweight, pip-installable libraries .
<span style="display:none">[^2_10][^2_11][^2_12][^2_13][^2_14][^2_15][^2_16][^2_17][^2_18][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: https://python-frontmatter.readthedocs.io/en/latest/api.html

[^2_2]: https://pypi.org/project/python-frontmatter/

[^2_3]: https://pypi.org/project/readtime/

[^2_4]: https://github.com/guedesfelipe/readtime_cli

[^2_5]: https://libraries.io/pypi/markdown-readtime

[^2_6]: https://pypi.org/project/markdown-analysis/0.0.4/

[^2_7]: https://stackoverflow.com/questions/32621299/creating-a-wpm-counter-for-a-phrase-then-output-the-time-taken

[^2_8]: https://hackr.io/blog/how-to-create-a-python-speed-typing-test

[^2_9]: https://pypi.org/project/readtime/1.0.4/

[^2_10]: https://www.youtube.com/watch?v=FblABqaKz_U

[^2_11]: https://github.com/mattjennings/remark-reading-time

[^2_12]: https://www.geeksforgeeks.org/javascript/design-a-typing-speed-test-game-using-javascript/

[^2_13]: https://www.youtube.com/watch?v=KnRynm9xdFQ

[^2_14]: https://docs.astro.build/en/recipes/reading-time/

[^2_15]: https://www.linkedin.com/posts/irfan-muhammad-182a73208_python-programming-learningbydoing-activity-7419977225413996544-dSQe

[^2_16]: https://bvgsoftware.com/blog/read-time-feature-for-react-markdown-blog/

[^2_17]: https://docs.python.org/3/library/typing.html

[^2_18]: https://github.com/alanhamlett/readtime


---

# which function that can detect if [[wiki-link]] if a markdown have kind of wiki-link inside?

None of the four libraries from the previous research natively detect `[[wiki-link]]` syntax. Here's the honest breakdown:

***

## `mrkdwn_analysis` — No Wiki-Link Support

`identify_links()` only detects standard Markdown links (`[text](url)`) and image links (`![alt](url)`). It does **not** handle `[[wiki-links]]`.[^3_1][^3_2]

***

## Best Options for Wiki-Link Detection

### 1. Python `markdown` built-in `wikilinks` extension

The standard `markdown` library ships with a `wikilinks` extension out of the box:[^3_3]

```python
import markdown
import re

content = post.content  # from python-frontmatter

# Detect/extract wikilinks with regex
wikilinks = re.findall(r'\[\[([^\]]+)\]\]', content)
print(wikilinks)  # ['wiki-link', 'another-page']

# Or convert them to HTML links
md = markdown.Markdown(extensions=['wikilinks'])
html = md.convert(content)
```


### 2. `mdx_wikilink_plus` — Richer Wiki-Link Support

`pip install mdx_wikilink_plus` — an extension to Python-Markdown that converts `[[wikilink]]` to relative links, supports `[[image.ext|alt=text]]`, absolute link passthrough, and custom base URL :

```python
import markdown
md = markdown.Markdown(extensions=['mdx_wikilink_plus'])
html = md.convert(content)
```


### 3. `mistune` + custom plugin

For extraction (not just rendering), `mistune` 3 supports registering inline parsers, so you can define a `wikilink_plugin` that captures both `[[Page]]` and `[[Page|Display Text]]` as typed tokens :

```python
from mistune import create_markdown
md = create_markdown(plugins=[wikilink_plugin])
```


### 4. Plain regex (simplest)

If you just need to detect/extract wiki-links without rendering them :

```python
import re
wikilinks = re.findall(r'\[\[([^|\]]+)(?:\|([^\]]+))?\]\]', content)
# Returns [('page-name', ''), ('page-name', 'display text')]
```

This handles both `[[page]]` and `[[page|display text]]` variants.

***

## Recommendation

| Goal | Best Tool |
| :-- | :-- |
| Just detect/extract `[[links]]` | `re.findall()` regex |
| Convert to HTML links | `markdown` + `wikilinks` extension |
| Advanced: `[[img\|alt=...]]` support | `mdx_wikilink_plus` |
| Custom token-based parsing | `mistune` + plugin |

For your use case as a developer working with Obsidian-style markdown, the **regex approach** paired with `python-frontmatter` is the most pragmatic — no extra dependency needed and gives you the raw link targets directly.
<span style="display:none">[^3_10][^3_11][^3_12][^3_13][^3_14][^3_15][^3_4][^3_5][^3_6][^3_7][^3_8][^3_9]</span>

<div align="center">⁂</div>

[^3_1]: https://github.com/yannbanas/mrkdwn_analysis

[^3_2]: https://github.com/yannbanas/mrkdwn_analysis/blob/main/README.md

[^3_3]: https://python-markdown.github.io/extensions/wikilinks/

[^3_4]: https://stackoverflow.com/questions/67940820/how-to-extract-markdown-links-with-a-regex/67942420

[^3_5]: https://stackoverflow.com/questions/77912770/how-to-extract-data-from-a-wikilinks

[^3_6]: https://git.fps.ee/markdown/.git/diff/docs/extensions/wikilinks.txt?id=87716ec3ab5b1e9e3c37d2fc5331ed95f3e311e9\&id2=27ec209b874bf30f03fc1c474d095f4ef67b3b72

[^3_7]: http://peter-hoffmann.com/2025/mistune-3-wikilink-inline-parser.html

[^3_8]: https://talk.jekyllrb.com/t/is-there-a-way-to-extend-the-markdown-syntax-to-allow-for-wiki-like-links-using-double-square-brackets-link-to-a-post/4256

[^3_9]: https://libraries.io/pypi/mrkdwn-analysis

[^3_10]: https://github.com/neurobin/mdx_wikilink_plus

[^3_11]: https://libraries.io/pypi/markdown-analysis

[^3_12]: https://python-frontmatter.readthedocs.io/en/latest/handlers.html

[^3_13]: https://docs.gitlab.com/user/project/wiki/markdown/

[^3_14]: https://pypi.org/project/markdown-analysis/

[^3_15]: https://forum.obsidian.md/t/wikilinks-in-yaml-front-matter/10052?page=4

