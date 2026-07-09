---
name: check-segments
description: List and inventory what automation segments are currently running for a profile. Use when the user asks "what segments do I have," "what's running," "show my automation," "what's set up," "am I covered," or wants to know if specific automation types are in place. Also use when comparing what's deployed against what should be deployed based on best practices.
---

# Check Segments Skill

## Context to Load Before Starting

1. `reference/MJ_API_REFERENCE.md` — for `GET /segments` endpoint
2. `user/MJ_COPILOT_LOG.md` — optional, load if the user wants to compare API state against what the Copilot deployed

Coverage mapping needs no template file — the five categories are inferred from the live segments (see Step 4). Comparing a segment against the current library version is a remote fetch (route to `review-segment`), not a bundled-file read.

---

## Overview

Fetch all segments for a profile, categorize them, flag anything outdated, and compare against the five core automation categories.

---

## Workflow

### Step 1 — Confirm Profile

If not already established, identify which profile to check.

### Step 2 — Fetch Segments

`GET /api/v5/segments` with `profileid` header. `ad_type` now returns the correct value for all datasets including `keywords_and_targets` and `ads` (the old `"unknown"` bug is fixed as of 2026-06-09). In the rare case a segment still shows `ad_type: "unknown"`, infer the category from the segment's action and trigger content (e.g., `create_negatives` → Search Term Negation, `set_state` with pause logic → Product Ad Management, `set_bid` with impression triggers → Impression Recovery).

### Step 3 — Categorize

Group segments by automation type:
- Bid Management (keywords, targets, keywords_and_targets)
- Budget Management (campaigns — budget actions)
- Search Term Negation (search_terms — create_negatives)
- Product Ad Management (ads/product-ads — state changes)
- Impression Recovery (keywords/targets — bid increases on impression triggers)
- Other (anything that doesn't map cleanly)

### Step 4 — Coverage Analysis

Compare against the five core automation categories. Report what's covered (✅) and what's missing (❌).

Flag potential issues:
- Segments that haven't run recently (check `last_run` field)
- Segments that are disabled (`enabled: false`)
- Segments with outdated patterns (detectable from trigger syntax — single conditions, no LET variables, etc.)
- Duplicate coverage (two bid management segments that might conflict)

### Step 4.5 — Check for Library Updates (present at the check)

After the coverage analysis, run an updates check against the library — but present the result immediately. The check overwrites the local cache as it runs, so the diff is one-shot; you cannot run it now and report later.

- **Shell runtimes:** `python tools/library.py check-updates`.
- **Web-fetch-only runtimes:** fetch the release manifest, diff each template's `last_updated` and the top-level `pack_version` against the cached copy in `user/.library-cache.json`, report, then rewrite the cache. See `docs/library.md` → update check for the exact procedure.

Surface the headline inline: "The library has a newer version of [template] you're running" or "[N] new templates since you last looked." If nothing changed, skip it silently.

### Step 5 — Present Results

Present the inventory and coverage analysis:

```
## Segments: [Profile Name]

### Inventory
| # | Segment Name | Type | Dataset | Enabled | Last Run |
|---|---|---|---|---|---|
| 1 | Core: Dynamic Bid Management | Bid Management | Keywords & Targets | ✅ | Apr 5 |
| 2 | Core: Search Term Waste Elimination | Search Term Negation | Search Terms | ✅ | Apr 5 |

### Coverage
- ✅ Bid Management: Core: Dynamic Bid Management
- ✅ Search Term Negation: Core: Search Term Waste Elimination
- ❌ Budget Management: Not set up
- ❌ Prod