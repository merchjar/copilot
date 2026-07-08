---
name: performance-check
description: Analyze account performance and diagnose what's driving changes. Use when the user asks "how am I doing?", "is it working?", "what's changed?", "check my performance", "why is my ACOS up?", "performance is down", or comes back after deploying segments and wants to see the impact. Also use when the user asks a general "why" question about their account metrics — not a specific segment behavior question.
---

# Performance Check

## When This Runs

The user wants to understand their account performance — whether it's improving, declining, or flat. This might be prompted by deploying segments, noticing a change in their Amazon dashboard, or just wanting a periodic health check.

**Important:** This skill follows the diagnostic hierarchy in docs/copilot.md. Start with the advertising fundamentals, not the segment mechanics. The user cares about their numbers — segments are just one possible explanation for what's happening.

## Context to Load

1. `reference/MJ_API_REFERENCE.md` — for preview and audit-log queries
2. `user/MJ_COPILOT_LOG.md` — previous review findings and deployed segment dates (baseline for comparison)
3. User preferences from `user/MJ_COPILOT_CONFIG.md` (already loaded)

If there's no prior review in the log, that's fine — still run the analysis. You just won't have a "before" snapshot for segment-specific comparison. Say: "I don't have a previous review to compare against, but I can still break down what's happening in your account right now."

---

## Workflow

### Step 1 — Establish the Time Window

Determine what period the user is asking about. Common patterns:
- "Since we set up segments" → use deployed segment date from log as the start of the comparison window
- "Last two weeks" / "since March" → use the explicit timeframe
- No timeframe specified → default to 14-day comparison (last 14 days vs. prior 14 days)

You need two periods: **current** and **prior** (same length, immediately preceding).

### Step 2 — Account-Level Metrics

Run two segment preview queries against the campaigns dataset — one per period — to get aggregate numbers.

**Default: offset relative ranges (always current)**

Current period payload:
```json
{
  "profile_id": "[profile_id]",
  "ad_type": "campaigns",
  "trigger": "let $spend = spend(0d..13d); let $sales = sales(0d..13d); let $acos = acos(0d..13d); impressions(lifetime) >= 0",
  "action": "set_state",
  "action_params": { "value": 1 }
}
```

Prior period payload: swap every `0d..13d` → `14d..27d`.

**If the user gave specific dates**, use literal date ranges instead:
```
spend(2026-03-30..2026-04-12)   // current
spend(2026-03-16..2026-03-29)   // prior
```

Pull totals from the `totals` object in the response — it aggregates across all rows without requiring pagination. Use `pagination.total` for active campaign count.

Present as the headline table:

| Metric | Prior Period | Current Period | Change |
|---|---|---|---|
| Total Ad Spend | $X,XXX | $X,XXX | +/- $X,XXX (+/-X%) |
| Ad-Attributed Sales | $X,XXX | $X,XXX | +/- $X,XXX (+/-X%) |
| ACOS | XX.X% | XX.X% | +/- X.X pts |
| Active Campaigns | N | N | +/- N |

This is the headline. Present it first — it frames everything that follows.

### Step 3 — Campaign-Level Breakdown

Compare campaign-by-campaign. Sort by absolute spend delta (largest increase first). Flag:

- **New campaigns** (spend in current period, zero in prior) — these are learning-phase launches and often the single biggest driver of ACOS increases. Call them out explicitly.
- **Scaling campaigns** (spend increased >50%) — check if ACOS held or deteriorated with scale.
- **Declining campaigns** (spend decreased >30%) — might be intentional (budget cuts) or a signal (low impression share, paused by automation).
- **ACOS blowouts** (ACOS increased >10 points) — these are your "what went wrong" candidates regardless of spend level.

Present the top 5-8 campaigns by impact with a clean table. Use the data presentation standard from docs/copilot.md.

### Step 4 — Root Cause Analysis

For each major delta driver from Step 3, categorize the cause:

| Cause Category | What to Look For | Example |
|---|---|---|
| New campaign launches | Campaigns with zero prior-period spend | "8 new campaigns account for $1,069 of the $1,346 spend increase at 35% blended ACOS — that's learning-phase behavior" |
| Bid level changes | Historical Bid Setter activity, manual bid adjustments, segment-driven bid increases | "Tennessee campaign scaled 3x after bid increases — ACOS went from 25% to 31%" |
| Budget shifts | Budget increases allowing more spend, budget caps constraining winners | "Your top performer is budget-capped at $100/day" |
| Seasonal / market | Same pattern last year, category-level trends | "This window was near-breakeven last year too — it's seasonal" |
| Segment activity | Audit log shows segment actions correlating with the metric change | "The bid management segment decreased bids on 12 keywords, but those keywords only represent $45 of total spend — not the driver" |

**Key principle:** Lead with the biggest impact driver, not the most technically interesting one. If 8 new campaigns explain 80% of the ACOS increase, say that first. Don't bury it after a segment conflict investigation.

### Step 5 — Segment Performance (If Relevant)

Now — and only now — check how automation is performing:

- Fetch recent audit log entries for deployed segments
- Summarize: runs, entities affected, failures
- Compare waste metrics against baseline (if one exists in the log)

If segments are clearly NOT the performance driver, say so plainly: "Your segments are running fine — the performance shift is driven by [the actual cause], not automation behavior."

If segments ARE contributing: quantify. "The bid management segment increased bids on 15 keywords in the Tennessee campaign, adding ~$200 in spend at 38% ACOS. That accounts for about 15% of the overall ACOS increase."

### Step 6 — Recommendations

Prioritize by dollar impact, not by what's easiest to fix through the Copilot:

- If new campaigns are the driver: "These campaigns are in learning phase — give them 2-3 more weeks before judging. If you want to limit exposure, reduce daily budgets on the worst performers."
- If bid levels are the driver: "The bid increases from [source] pushed spend up faster than sales followed. Options: walk bids back manually, tighten the bid management segment's ceiling, or accept the higher ACOS for volume."
- If budget caps are the driver: "Your best campaign is hitting its budget cap every day — it's leaving money on the table. Increase budget or let the budget management segment handle it."
- If segments caused unintended behavior: Offer to tune (→ hand off to `review-segment`) or troubleshoot (→ `troubleshoot`).
- If it's seasonal: "This is a seasonal pattern — your 2024 numbers show the same dip in this window. The right move is probably patience, not settings changes."

**One clear recommendation first, then alternatives.** Don't present a menu of 5 equally weighted options.

### Step 7 — Update Log

Append current metrics to `user/MJ_COPILOT_LOG.md` under Account Reviews so the next performance check has a fresh baseline. Include: date, period compared, account-level metrics, top campaign deltas, root cause summary, and any actions taken.

---

## Quick Mode

If the user just wants a fast pulse ("quick check" / "how's it looking?"), run the audit log query only:

> Your segments ran [N] times this week — [N] search terms negated, [N] bid adjustments, [N] budget changes. No failures. Everything's running clean.

Or if there are issues:

> [Segment name] failed on [N] of [M] attempts this week. Want me to dig into why?

Quick mode is segment-focused because the user is asking specifically about automation, not about performance. If they follow up with a performance question, switch to the full workflow.
