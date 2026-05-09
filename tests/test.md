---
title: Test Note
tags: [project, documentation, obsidian]
created: 2024-01-15
status: active
aliases:
---

# Test Note

This is a test markdown file for unit testing the `Markdown` class.

## Tags

Inline tags like #python and #testing should be detected.

Nested tags like #project/active and #topic/obsidian/plugins should also work.

## Links

Here are some wiki links:
- [[another-note]]
- [[note with spaces]]
- [[target-note|Display Text]]
- [[page]]

And some markdown links:
- [External Link](https://example.com)
- [Relative Link](./another-page.md)

## Code

```python
# This #comment should not be extracted as a tag
print("hello")
```
