---
name: troubleshoot
description: Debug why a segment took an action (or didn't). Use when the user asks "why did this segment pause/change/negate my keyword/search term/campaign," "why isn't this doing anything," "this segment isn't working," "debug this," "explain why X happened," or wants to understand unexpected automation behavior before deciding what to do.
---

# Troubleshoot Skill

## Context to Load Before Starting

1. `reference/MJ_API_REFERENCE.md` — for preview endpoint
2. `reference/V2_SYNTAX_REFERENCE.md` — for tracing segment logic

Do NOT load creation guidelines — this skill diagnoses, it doesn't create.

---

## Scope Check — Is This Actually a Troubleshoot?

Before diving in, check whether the user is really asking about a specific segment action or about overall performance:

- **"Why did this segment pause my keyword?"** → This skill. Proceed.
- **"This segment isn't doing anything"** → This skill. Proceed.
- **"Why is my ACOS up?" / "performance is down" / "things aren't working as well"** → This is a performance question, not a segment question. Redirect to `performance-check`. Say: "Let me start by looking at your overall numbers — the answer might not be in the segments." Follow the diagnostic hierarchy in docs/copilot.md.
- **"The segment never ran" / "it's stuck on Syncing" / "it's been Syncing for hours/days" / "it shows enabled but nothing happened"** → This usually is NOT a logic problem and not something this skill traces. A segment that validates and previews fine but never executes or sticks at "Syncing" is almost always an **app-side sync/scheduler issue**, not a flaw in the DSL the Copilot wrote. Don't re-debug the trigger. Instead: (1) confirm the trigger previews cleanly (a quick preview proves the logic is sound), then (2) say plainly: "The logic checks out in preview, so this looks like an app-side sync issue rather than a problem with how the segment was built. That's handled by the Merch Jar team, not something I can fix from here." (3) Offer to draft a short support message: "Want me to draft a note to Merch Jar support with the segment name, ID, profile, and when it got stuck?" This resolves the issue through the right channel and avoids the misread that "the AI built it wrong."

The distinction: troubleshoot traces a specific segment's logic on a specific entity. If the user hasn't named a segment and an entity, they're probably asking a bigger question.

---

## Overview

Explain why a segment acted (or didn't act) on a specific entity. Use preview data and the segment's diagnostic properties to trace the logic in plain advertising language.

---

## Workflow

### Step 1 — Identify Segment and Entity

Get from the user:
- Which segment (name, ID, or paste DSL)
- Which entity they're asking about (keyword text, search term, campaign name, ASIN)
- What happened (or what didn't happen) that they're asking about

If they only give one of these, ask for the other. Can't trace logic without both.

### Step 2 — Fetch Segment if Needed

If the user gives a segment name or ID, fetch it: `GET /api/v5/segments/:id`. If they paste DSL, use that directly.

### Step 3 — Preview with Diagnostics

Run the segment in preview mode against the current data. Use enough pagination to find the specific entity the user is asking about. Look for the entity in the `data` array — check its `$reason` and `$planned_action` values.

If the entity doesn't appear in the preview results at all: that means the entity doesn't match the segment trigger. Note which part of the final filter is excluding it. If the result set is large, increase the page size or add a filter to narrow down to the specific entity.

### Step 4 — Trace the Logic

**Follow the data presentation standard in docs/copilot.md** when showing any preview data. For troubleshooting specifically, show only: entity name, $reason, $planned_action, and the 1-2 metrics that explain the outcome.

Walk through the key conditions step by step using concrete numbers:

"This keyword had 45 clicks in the last 30 days with zero orders. The segment's threshold is 20 clicks — so it qualified. It wasn't in your protected list, and it hadn't already been negated. All conditions were met, so it was negated."

Or: "This keyword wasn't included because it only had 8 clicks in the last 30 days — the segment requires at least 10 clicks before acting."

Focus on the $reason value first — it's designed to explain the outcome. Translate it into plain advertising language.

### Step 5 — Suggest Fixes

If the behavior is unintended, suggest specific settings changes:
- "If you want to give keywords more time before negating, increase $clicks_threshold from 20 to 40"
- "If you want to protect this keyword specifically, add its text to $protected_terms"
- "If the cooldown period is too long, reduce $cooldown_period from 5d to 2d"

Offer to make the change using the `review-segment` skill (it will preview the impact before deploying the updated version).
