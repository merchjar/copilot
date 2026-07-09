---
name: audit-log
description: Show what automation segments have done recently — bid changes, negations, budget adjustments, pauses. Use when the user asks "what did my segments do," "show my audit log," "what happened this week," "any changes," "what changed recently," or wants to know the impact of their automation. Also use proactively when the user asks "is my automation working."
---

# Audit Log Skill

## Context to Load Before Starting

1. `reference/MJ_API_REFERENCE.md` — for `GET /audit-logs` endpoint

Do NOT load syntax reference, creation guidelines, or the template library — this skill reads history, not segments.

---

## Overview

Pull recent audit log entries for a profile and summarize what automation has done. Surface anomalies. Present impact in plain English with entity counts and — where calculable — dollar amounts.

---

## Workflow

### Step 1 — Confirm Profile and Timeframe

Identify profile. Default timeframe: last 7 days. Adjust based on user request ("this month," "since Monday," "last 30 days").

### Step 2 — Fetch Audit Logs

`GET /api/v5/audit-logs` with `profileid` header. Paginate through results to cover the requested timeframe (most recent first). If the endpoint supports date filtering, use it to limit the response. Consult the API reference (loaded at skill start) for exact response structure — field names matter here.

### Step 3 — Summarize by Segment

Group entries by segment (use the segment identifier field from the API response). For each segment, extract:
- Segment name
- Total entities evaluated
- Successful changes vs. failures
- Last run timestamp
- What the segment does (from action type)

Consult the API reference for exact field paths — don't assume field names.

### Step 4 — Flag Anomalies

Things to call out:
- High failure rate (>10% of actions failing)
- Segments that haven't run in the expected window (daily segment with no run in 3+ days)
- Unusually high action counts (segment affecting far more entities than expected — might indicate an overly aggressive trigger)
- All-or-nothing patterns (segment ran but affected 0 entities every time — trigger may be too restrictive)

### Step 5 — Present Summary

Plain-English summary of what happened:

```
## Audit Log: [Profile Name] — Last 7 Days

Your segments made changes on [N] separate runs:

**Dynamic Bid Management** — ran daily, 23 total runs
  - Adjusted bids on 142 keywords (138 successful, 4 failed)
  - Mix of increases and decreases based on ACOS performance

**Search Term Waste Elimination** — ran daily, 23 total runs
  - Negated 31 search terms
  - No failures

⚠️ **Budget Management** — last run 4 days ago (expected: daily)
  You may want to check if this segment is still enabled.
```

Offer to investigate anomalies with the `troublesho