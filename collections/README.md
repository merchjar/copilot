# Collections

Curated bundles of Library items (templates, skills, property sets) with a story.
Each collection is one Markdown file with YAML frontmatter; `tools/build_manifest.py`
catalogs them under `collections` in `manifest.json`, and the website renders a
page per collection. Videos and posts link to collection URLs, not the landing page.

```markdown
---
id: core-six              # must match the filename
name: The Core Six
description: one line
goal: cut-waste           # cut-waste | grow | protect | understand | set-up
featured: true            # shows in the Start here row
items:                    # ordered template / skill / property-set ids
  - core-search-term-waste-elimination
---
The story (why these belong together, in what order, what to expect).
```
