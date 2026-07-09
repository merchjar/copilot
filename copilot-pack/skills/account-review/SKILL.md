---
name: account-review
description: Full account diagnostic — runs multiple queries to find waste, automation gaps, and opportunities across the entire account. Use when the user explicitly asks for a comprehensive review, full audit, or "check my whole account." The quick scan (offered at session start) covers initial search term waste — this skill goes deeper across all categories.
---

# Account Review (Full Audit)

## When This Runs

This is the deliberate, comprehensive review — not the default first interaction. Users arrive here when they:
- Explicitly ask for a full audit ("review my account," "check everything," "what should I automate?")
- Want to go deeper after the quick scan results ("what else is wrong?," "check more things")
- Are doing a periodic checkup (monthly, after onboarding new clients)

The quick scan (in docs/copilot.md) already covers search term waste. This skill picks up where that left off.

## Context to Load Before Starting

1. `reference/MJ_API_REFERENCE.md` — needed for preview queries and segment fetching
2. `user/MJ_COPILOT_LOG.md` — load if the user has done a previous review (compare findings)

Coverage mapping needs no template file — the five categories are inferred from the live segments (see Step 2). Named-template recommendations pull specifics from the GitHub library (see `docs/library.md`), not a bundled file.

Do NOT load V2_SYNTAX_REFERENCE.md or SEGMENT_CREATION_GUIDELINES.md — this skill reads data, it doesn't write segments.

---

## Single Account Flow

### Step 1 — Confirm Profile

Identify which profile to analyze. If the user hasn't specified:
- If there's only one managed profile in config, confirm and proceed
- If there are multiple, list them with 30-day spend and ask
- If `Default Profile` is set and seems right, confirm rather than asking

### Step 2 — Check What's Already Running

Fetch existing segments: `GET /api/v5/segments` with `profileid` header.

**Framing:** the five core automations are deployed to every account by the app (disabled until enabled), so on most accounts this snapshot is "what's already live or installed," not "what you'd have to build from scratch." A disabled core with no run history is installed-but-off — present it as a one-click enable, not a gap. A category is only a true gap if no segment covers it at all (the user deleted the core).

Map each segment to the five core automation categories:

| Category | What to look for |
|---|---|
| Bid Management | Bid adjustments based on ACOS or performance ratios |
| Budget Management | Budget changes based on utilization or performance |
| Search Term Negation | `create_negatives` action on search terms |
| Product Ad Waste | State changes on product ads based on spend/orders |
| Impression Recovery | Bid increases triggered by impression drops |

**Present as a quick coverage snapshot — not a report section:**

> Here's what you have running:
> - ✅ Search term negation: "ST Waste Elimination v1.1"
> - ✅ Bid management: "Dynamic Bids"
> - ❌ Budget management — nothing set up
> - ❌ Product ad waste — nothing set up
> - ❌ Impression recovery — nothing set up

**Flag outdated segments:** Single-condition triggers, no multi-period logic, missing $reason/$planned_action diagnostics, no state filtering. Mention these as upgrade opportunities — don't lecture.

**Note:** Bid management covers both underperforming keywords AND unmanaged keywords (those with no bid history). Don't present unmanaged keywords as a separate coverage gap — they're handled by the same segment.

**For existing Merch Jar users:** This step is especially important. They may have Recipes or Smart Bids running. Check audit logs (`GET /api/v5/audit-logs`) for recent activity — the `source_type` field shows `"recipe"` for both Recipes and Segments, and `meta.event` contains the automation name and trigger logic. If you find Recipe activity, summarize what the Recipes are doing and map them to the same five coverage categories. This gives the user a complete picture without requiring them to manually report what's running. If no audit log activity is found, ask: "Do you also have Recipes or Smart Bids active? The audit log didn't show recent activity, but there may be automation that hasn't run recently."

### Step 2.6 — Check for Library Updates (present at the check)

Right after the coverage snapshot, run an updates check against the library — but only if you present the result immediately. The check overwrites the local cache as it runs, so the diff is one-shot: you cannot run it now and report later.

- **Shell runtimes:** `python tools/library.py check-updates`.
- **Web-fetch-only runtimes:** fetch the release manifest, diff each template's `last_updated` and the top-level `pack_version` against the cached copy in `user/.library-cache.json`, report, then rewrite the cache. See `docs/library.md` → update check for the exact procedure.

Surface the headline inline: "The library has a newer version of [template] than the one you're running" or "[N] new templates since you last looked, here they are." If nothing changed, skip it silently and continue to the diagnostics.

### Step 2.5 — Reference Quick Scan Results

If the quick scan already ran earlier this session, reference those results before moving to new diagnostics. Don't silently skip them — the user needs to see the full picture in one place.

> "When I first connected, I found [N] search terms that should probably be negated — $X,XXX in the last 90 days ($XX,XXX lifetime). That's still the biggest finding so far. Let me check what else is going on."

This ensures the search term waste is part of the review narrative even though you're not re-running the query. If the quick scan didn't run (e.g., user jumped straight to account review), run the search term waste query as Query 1 in Step 3.

### Step 3 — Diagnostic Queries

Run queries conversationally — one at a time, presenting findings after each, asking if the user wants to continue or act on what they've seen. Don't batch all 4 queries silently and dump a report.

**Skip the search term waste query if the quick scan already ran it this session** (you referenced those results in Step 2.5). Start with the next most useful query.

> **Important:** Preview queries take `profile_id` in the request body (NOT as a `profileid` header). Always include `profile_id`, `trigger`, `ad_type`, `action`, and `action_params` in the JSON body.

> **Totals field naming:** The `totals` object uses field names with the time period suffix from the query (e.g., `cost_lifetime`, `cost_30d`). Use `cost_*` for spend/waste amounts.

**Query 1: Keyword Waste (30-day active bleed)**
```json
{
  "profile_id": "[profile_id]",
  "ad_type": "keywords",
  "trigger": "let $spend_30d = spend(30d); let $clicks_30d = clicks(30d); let $orders_30d = orders(30d); let $reason = case($orders_30d = 0 and $clicks_30d >= 10 => \"No orders — spending with zero conversions in 30d\", else \"Under threshold\"); let $planned_action = case($orders_30d = 0 and $clicks_30d >= 10 => \"Reduce bid\", else \"No action\"); spend(30d) > 0 and orders(30d) = 0 and clicks(30d) >= 10 and state = \"effectively enabled\"",
  "action": "set_bid",
  "action_params": { "direction": "decrease-%", "value": 10, "source": "value" }
}
```

Present headline + top 5 table. Include the bid for each keyword — it helps the user immediately see if a bid is unreasonable.

> **[N] keywords spending with zero orders in the last 30 days — $X,XXX wasted.**
>
> | Keyword | Match | 30d Spend | Clicks | Bid |
> |---|---|---|---|---|
> | ... | ... | ... | ... | ... |

**After presenting:** Flag any notable patterns in the results:
- Brand name keywords spending with no orders (e.g., their own brand terms appearing in the list — this is always a reaction moment)
- Keywords on very low bids accumulating spend through volume
- Keywords that have never had their bids adjusted (check `last bid change` — if null, mention it inline: "Three of these have never had their bids adjusted — they're running on whatever bid was set when they were created")

The unmanaged keyword callout is folded into this finding rather than presented as a separate diagnostic. It answers the "so what" — they're wasting money *because* nobody's managing them. This naturally sets up the bid management segment recommendation.

**Transition:** "These are the first candidates for bid management automation. Want me to check your campaign budgets next, or address these first?"

**Query 2: Budget-Capped Campaigns**
```json
{
  "profile_id": "[profile_id]",
  "ad_type": "campaigns",
  "trigger": "let $today_util = spend(0d..0d) / budget; let $yesterday_util = spend(1d..1d) / budget; let $reason = case($yesterday_util >= 0.9 => \"Hit budget cap yesterday\", $today_util >= 0.9 => \"Hitting cap today\", else \"Under cap\"); let $planned_action = case($yesterday_util >= 0.9 or $today_util >= 0.9 => \"Increase budget\", else \"No action\"); state = \"effectively enabled\" and ($today_util >= 0.9 or $yesterday_util >= 0.9)",
  "action": "set_budget",
  "action_params": { "direction": "increase-%", "value": 10, "source": "value" }
}
```
Present: "[N] campaigns hitting their daily budget cap." Note: `spend(0d..0d)` is partial today — weight findings toward yesterday's data.

**If zero campaigns are capped**, say so briefly and move on — don't dwell on a non-finding.

**Query 3: Search Term Waste (only if quick scan didn't run)**
Use the quick scan from docs/copilot.md.

**Optional Query: Campaign Structure Scan**

Don't run by default. Offer after the core diagnostics: "I can also check your campaign structure — look for campaigns that are enabled but not doing anything, or budgets that are way out of line with actual spend. Want me to take a look?"

If the user says yes:
```json
{
  "profile_id": "[profile_id]",
  "ad_type": "campaigns",
  "trigger": "let $daily_avg = spend(30d) / 30; let $utilization = case(budget > 0 => $daily_avg / budget, else 0); let $reason = case(state = \"effectively enabled\" and spend(90d) = 0 => \"Enabled but zero spend in 90 days\", state = \"effectively enabled\" and $utilization < 0.05 and spend(30d) > 0 => \"Severely under-utilized — budget far exceeds actual spend\", state = \"effectively enabled\" and $utilization > 0.90 => \"Budget capped — spending more than budget allows\", else \"OK\"); let $planned_action = case(spend(90d) = 0 => \"Review — consider pausing or archiving\", $utilization < 0.05 and spend(30d) > 0 => \"Right-size budget to actual spend\", $utilization > 0.90 => \"Increase budget if converting well\", else \"No action\"); state = \"effectively enabled\"",
  "action": "set_budget",
  "action_params": { "direction": "set-to-$", "value": 50, "source": "value" }
}
```

Present as a structural overview, grouped by issue type:

> **[N] enabled campaigns — here's how they break down:**
> - **[N] ghost campaigns** — enabled but zero spend in 90 days. These are cluttering your account and should probably be paused or archived.
> - **[N] over-budgeted** — budgets far above actual spend (e.g., $500 budget on a campaign spending $1/day). Not urgent, but budget management automation would clean this up.
> - **[N] budget-capped** — spending at or above their daily limit. If these are converting well, they need more room.
> - **[N] healthy** — budgets roughly aligned with spend.
>
> The ghost campaigns are worth cleaning up manually — no automation needed, just pause them. The budget mismatches are what the Adaptive Budget Management segment handles.

This is a good agency demo finding — "75 campaigns enabled, 18 of them doing nothing" is a visual that communicates neglect immediately.

### Step 4 — Summary + Recommendations

After running through queries conversationally, pull it together:

> **Summary for [Profile Name]:**
> - Search term waste: $X,XXX in 90d / $XX,XXX lifetime across [N] terms
> - Keyword waste (30d): $X,XXX on [N] keywords with zero orders ([M] of those have never been optimized)
> - Budget-capped campaigns: [N] campaigns
> - Campaign structure: [N] ghost campaigns, [N] over-budgeted (if scan was run)
>
> **Automation coverage:** [quick ✅/❌ list]
>
> **Where I'd start:** [Highest dollar impact action — usually search term negation, then bid management]

Then offer to start building. Hand off to `build-segment` for each recommended action, naming the template by its library id (e.g. `core-search-term-waste-elimination`) so the build skill fetches the right one. For a core category that's present-but-disabled, frame the hand-off as "enable the one that's already installed," not "build a new one." Pull any specific template name and one-line description from the library manifest (see `docs/library.md`), not a bundled file.

**Recommendation framing:** Connect each automation recommendation to a specific finding from the review. Don't just list segment names — explain what each one fixes:
- "Search Term Waste Elimination handles the [N] terms we found — negates the existing waste and catches new ones going forward"
- "Dynamic Bid Management covers those [N] bleeding keywords, including the ones that have never been touched — adjusts bids based on actual performance"
- "Adaptive Budget Management right-sizes the [N] over-budgeted campaigns and prevents budget caps on your winners" (only recommend if the campaign structure scan surfaced budget issues)

### Step 5 — Log It

After the review is complete, append findings to `user/MJ_COPILOT_LOG.md` under `## Account Reviews`. Include date, profile, key numbers, and what was acted on.

If a previous review exists, compare: "Since your last review on [date], [metric] has [improved/worsened]."

---

## Agency Portfolio Flow

For users with multiple managed profiles.

### Step 1 — Portfolio Overview

List all managed profiles sorted by 30-day spend descending:

| # | Profile | Country | 30d Spend |
|---|---------|---------|-----------|
| 1 | Brand A | US | $45,200 |
