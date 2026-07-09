---
name: review-segment
description: Review an existing segment against current quality standards and upgrade it if needed. Use when the user pastes a segment and asks if it's good, asks to review or audit a segment, says "is this up to date," "check this against standards," "upgrade my segment," "tune this segment," "adjust the settings on this," or wants to know if their existing logic is correct. Also use when a segment fetched from the API looks outdated (missing diagnostics, simple single-condition triggers, hard-coded thresholds).
---

# Review Segment Skill

## Context to Load Before Starting

1. `reference/V2_SYNTAX_REFERENCE.md` — for parsing and understanding the DSL
2. `reference/SEGMENT_CREATION_GUIDELINES.md` — for standards comparison
3. The matching library template — if the segment maps to a known category, fetch it by id for comparison (see `docs/library.md`). This is a remote fetch, not a bundled file. If the library is unreachable, fall back to comparing against `SEGMENT_CREATION_GUIDELINES.md` and tell the user the live template couldn't be fetched.

Do NOT load `reference/MJ_API_REFERENCE.md` unless the user wants to preview/deploy after the review.

---

## Overview

Evaluate an existing segment against current quality standards. Produce a structured findings report and offer an upgraded version if issues are found.

---

## Workflow

### Step 1 — Receive the Segment

Two ways the user provides a segment:
- Pastes DSL directly into chat
- Gives a segment name or ID → fetch via `GET /api/v5/segments/:id`

If fetching via API, load `reference/MJ_API_REFERENCE.md` first.

### Step 2 — Parse and Categorize

Identify:
- What the segment does (bid management, search term negation, budget management, etc.)
- Which template category it maps to (if any)
- Current version number (from header comment, if present)

Fetch the matching library template for comparison if the segment maps to a known category (`library.py fetch <id>` in shell, the raw URL from the manifest in web-fetch runtimes — see `docs/library.md`). If the fetch fails, degrade gracefully: compare against `SEGMENT_CREATION_GUIDELINES.md` and tell the user you couldn't pull the current library version.

### Step 3 — Standards Check

Evaluate against quality standards. Categorize findings:

**Required fixes (non-negotiable):**
- Missing `state = "effectively enabled"` filter (where applicable)
- Missing or incorrect safe array defaults
- Using `does not contain any` for exclusion filters — MUST be `does not contain all`. The `any` variant uses OR logic which makes the exclusion silently pass everything. See V2_SYNTAX_REFERENCE.md Array operators section for full explanation.
- Missing `$reason` or `$planned_action` diagnostics (or using old `$result` name)
- No version header
- Hard-coded percentage thresholds instead of `target acos` integration

**Recommended improvements:**
- Missing multi-period data selection (single fixed window only)
- No cooldown check using `is_null()` pattern
- No CPC-based bid limits
- Poor variable naming (doesn't follow naming conventions)
- Comments missing or unclear
- `$reason` doesn't cover all major logic paths

**Observations (not errors):**
- Segment is simpler than the current core template for the same use case
- Logic uses patterns that work but aren't current convention

### Step 4 — Report Findings

Present findings clearly, organized by severity. Example:

```
## Segment Review: [Segment Name]
Version: [found] → should be [recommended]

### Required Fixes
1. Missing state filter — add `state = "effectively enabled"` to the final filter
2. Uses $result — rename to $planned_action (same behavior, clearer column header)

### Recommended Improvements
3. Single 30-day window only — consider adding multi-period data selection (7/14/30d)
4. No cooldown check — add is_null(last bid change) pattern to prevent rapid re-adjustments
5. Hard-coded 40% ACOS threshold — replace with target acos integration

### Looks Good
- Safe array defaults in place
- Conservative bid change (5%)
```

### Step 5 — Offer Upgrade

Produce an upgraded version of the segment with all required fixes applied and recommended improvements incorporated. Preserve the core intent and any custom logic 