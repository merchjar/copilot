---
name: check-segments
description: List and inventory what automation segments are currently running for a profile. Use when the user asks "what segments do I have," "what's running," "show my automation," "what's set up," "am I covered," or wants to know if specific automation types are in place. Also use when comparing what's deployed against what should be deployed based on best practices.
---

# Check Segments Skill

## Context to Load Before Starting

1. `reference/MJ_API_REFERENCE.md` — for `GET /segments` endpoint
2. `templates/README.md` — for automation coverage mapping
3. `user/MJ_COPILOT_LOG.md` — optional, load if the user wants to compare API state against what the Copilot deployed

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
- ❌ Product Ad Waste: Not set up
- ❌ Impression Recovery: Not set up

### Issues
- ⚠️ [Segment Name] hasn't run in 5 days (expected: daily)
- ⚠️ [Segment Name] uses outdated patterns — missing multi-period logic and diagnostics
```

Offer natural follow-up:
- For missing coverage: "Want me to build a [Search Term Waste Elimination] segment?"
- For outdated segments: "This segment looks like it's missing some of the safeguards in the current template. Want me to review it?"
- For disabled segments: First cross-reference `user/MJ_COPILOT_LOG.md`. If the log shows `Created (disabled)` and no later enable entry, this is a pending-enable segment — surface as "This segment is saved but never got enabled — want me to preview it and turn it on?" If the log shows it was enabled and later disabled (or has no matching log entry and has run history), treat it as an intentional disable — surface as "This segment is disabled — do you want to re-enable it or find out why it's off?"
