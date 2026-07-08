---
name: build-segment
description: Build and deploy a new Merch Jar automation segment. Use when the user wants to create automation, set up bid management, automate search term negation, configure budget automation, or says "build a segment," "automate my [bids/budget/search terms]," "I want to automate X," "help me with [waste/impressions/budget]," or accepts a recommendation from account review. Also use when the user describes a business goal that maps to a segment (e.g., "I'm wasting money on bad search terms," "my bids are all over the place," "some campaigns keep hitting their budget cap").
---

# Build Segment Skill

## Context to Load Before Starting

1. `reference/MJ_API_REFERENCE.md` — for validate, preview, create, and PATCH endpoints
2. `reference/V2_SYNTAX_REFERENCE.md` — for writing valid DSL
3. `reference/SEGMENT_CREATION_GUIDELINES.md` — for quality standards and patterns
4. `templates/README.md` — to identify the right template
5. Specific template file (once the right template is identified — load only that one)
6. User preferences from `user/MJ_COPILOT_CONFIG.md` (already loaded)

---

## Overview

Guide the user from goal → deployed segment. Two personas in one skill:

**Guided mode (default):** Users see plain English throughout. Settings explained in advertising terms. DSL shown only at the final review stage, and only if the user wants to see it.

**Power-user mode:** Full DSL visible and editable. Switch to this mode when: user pastes DSL, references specific DSL syntax, says "show me the code" or "write a segment" (vs. "automate" or "set up"), or otherwise signals technical comfort.

> **Deployment Safety Protocol applies throughout — no exceptions, no skill-specific overrides.** See docs/copilot.md → Deployment Safety Protocol. Every create path runs: pre-flight duplicate check (Step 2) → settings confirmation (Step 4) → preview (Step 6) → deploy disabled (Step 7) → explicit enable prompt (Step 8). An update path uses PATCH, not POST (Step 7 — Update Path). Violating any of these has caused real account damage — they are preconditions, not suggestions.

---

## Workflow

### Batch Build Mode

When the user wants to build multiple segments at once — typically after an account review ("fix all of this," "build everything we talked about," "set up automation for all of that") — use batch build mode:

1. **Present the plan.** List every segment you're going to build, in order, with a one-line description of what each one fixes:
   > I'll build three segments:
   > 1. **Search Term Waste Elimination** — negates the 732 wasteful terms we found
   > 2. **Dynamic Bid Management** — adjusts bids on those bleeding keywords and optimizes the unmanaged ones
   > 3. **Adaptive Budget Management** — right-sizes the 36 over-budgeted campaigns and prevents budget caps
   >
   > I'll use your **[Target ACOS from config]** and conservative defaults. All three will be created disabled — I'll preview each one, and you'll enable them when you're ready. Want me to go ahead, or do you want to customize settings first?
   >
   > *(Pull Target ACOS from `user/MJ_COPILOT_CONFIG.md` → User Preferences → Default ACOS targets. If not set, ask before proceeding.)*

2. **If they say go ahead:** For each segment, run the full protocol — pre-flight duplicate check, settings confirmation (compressed), validate (if needed), preview, DSL display (if show_work: full), confirmation gate (if require_approval: true), deploy disabled, enable prompt. Even in batch mode, the preview and the disabled-deploy step are not skippable. Between segments, narrate transitions briefly: "Search term negation is saved as disabled. Want me to enable it now, or move to bid management first and enable them together at the end?" A common batch pattern is "build all disabled, enable at the end after I've reviewed them in the app" — offer this explicitly.

3. **If they want to customize:** Drop into single-segment guided mode for that segment. After it's deployed, return to batch mode for the rest.

4. **Between segments:** Brief transition. Don't re-explain the template concept or walk through the full settings each time.

5. **After all segments are deployed:** Summary with all segment IDs and their enabled/disabled status. Offer a batch enable: "Want me to enable all three now, or review them in the app first?" Then offer next steps.

This mode is designed for the common post-review flow and for demos where you want the "watch it build everything" moment. The code display is the visual — let the DSL speak for itself. If `show_work: full` is active, apply the Show Your Work display for each segment in the batch before it deploys — same format as single segment mode. The sequence becomes: plan → pre-flight → settings check → preview → DSL block → confirm → deploy disabled → enable prompt, repeated per segment.

---

### Single Segment Mode (Default)

### Step 1 — Understand the Goal

If the user described a business goal ("I'm losing money on bad search terms"), translate it to the appropriate template. If the user specified a segment type directly ("build a search term negation segment"), proceed.

Use `templates/README.md` to match goal → template. If no template fits, build from scratch using the guidelines.

Tell the user what template you're going to use and why before loading it. Example: "For search term waste, I'll use the Search Term Waste Elimination template — it handles zero-order terms, inefficient converters, and ACOS-based negation in one segment. Let me load it up."

### Step 2 — Pre-flight Duplicate Check (mandatory)

Before anything else on the API side, call `GET /api/v5/segments` with the `profileid` header and scan the existing list for the active profile. Look for:

- Exact name match (case-insensitive) with the segment you plan to name
- Same `ad_type` + `action` serving the same purpose (another `search_terms` / `create_negatives` segment, another `keywords` / `set_bid` segment, etc.)

**Log reconciliation (piggyback on this same call):** Compare the GET response against `user/MJ_COPILOT_LOG.md` entries for this profile. If a logged segment ID is missing from the response, mark the log entry as deleted in place (update the existing row with `Status: Deleted (reconciled [date])` rather than appending a new one). Note the cleanup to the user in one line: "Cleaned up [N] log entries for segments that are no longer on this profile."

**Branching:**
- **No match** → proceed to Step 3.
- **Match found on name or purpose** → surface it: "There's already a segment named '[existing name]' on this profile (ID: [id], currently [enabled/disabled]) — it [one-line summary of what it does]. Update it instead, or create a separate new segment?" Default recommendation: update.
  - If the user says update, modify, adjust, tune → switch to the **Update Path** (Step 7 — Update Path).
  - If the user explicitly says "create a new one anyway" → proceed to Step 3 with a distinguishing name suffix.

Never silently POST when a duplicate exists. Never create a new segment when the user asked to modify an existing one.

### Step 3 — Customize Settings

Walk through the user-adjustable settings for the selected template. Group them as the template does (Core Settings, Strategy Settings, etc.). Explain each one in plain English — what it does, what the current default means in practice.

Pre-populate from config where possible:
- Automation Style → adjust default thresholds (conservative = larger safety margins, moderate = template defaults, aggressive = faster reaction)
- Protected campaigns → pre-fill `$exclude_campaigns`
- Campaign naming conventions → suggest smart `$include_campaigns` / `$exclude_campaigns` values
- Account type → if KDP, note that standard metrics are used and adjust expectations accordingly

For each setting, show: current default → what it does → ask if they want to change it or keep it.

**Always ask about protected terms** for segments that negate or pause. Prompt specifically: "Do you want to protect any branded terms, product names, or competitor ASINs from being negated?" Pre-fill from config if `$protected_terms` is set. For search term segments, ASIN-pattern search terms (e.g., b0xxxxxxxx) are common — ask if they should be excluded.

**For bid management segments:** Apply the same protected-item logic. Ask: "Are there any keywords or ASINs you want to keep off bid automation — branded keywords with fixed bids, or anything you've manually tuned that you don't want the segment to touch?" Pre-fill from config if `$protected_keywords` is set. This mirrors the protected terms question for search term negation and keeps behavior consistent.

**Don't overwhelm.** Core Settings first. Offer "keep defaults for the rest" before going into Strategy/Advanced settings. Most users only need to touch Core Settings.

### Step 4 — Settings Confirmation (before writing DSL)

After walking through settings, pause and read back the 3–4 most important configured values in plain English before generating any DSL. This is the last cheap moment to adjust something without rewriting code.

Example (search term negation):

> Here's what I'm about to build:
> - **Click threshold before negating:** 20 clicks with zero orders (conservative default)
> - **ACOS efficiency threshold:** negate converting terms running above 4x your Target ACOS
> - **Protected terms:** [list from config, or "none set — nothing will be spared, and you can add protections later"]
> - **Schedule:** daily
>
> Anything you want to change before I write it?

Example (bid management):

> Here's what I'm about to build:
> - **Target ACOS:** 30% (from your config)
> - **Bid adjustment range:** -10% to +10% per run (conservative)
> - **Cooldown:** 2 days between changes on the same keyword
> - **Protected keywords:** [list or "none set"]
>
> Anything you want to change before I write it?

Wait for "looks good," "go ahead," or an adjustment. Only proceed to Step 5 after this confirmation.

In batch build mode, this step collapses to a single compact confirmation per segment (key thresholds + protected items only). In power-user mode, the user may skip it with "just write it" — honor that, but the preview (Step 6) and disabled deploy (Step 7) still apply.

### Step 5 — Validate

**Check `templates/README.md` first.** The manifest has two verification columns: `Syntax validated` and `Preview verified`. The skip rule depends on both:

- **Template is Preview verified (✅ in both columns):** Skip the validate API call and proceed directly to preview. Say: "Using the confirmed core template — previewing against your live data now."
- **Template is Syntax validated only (✅ syntax, ⚠️ preview):** Still skip validate, but expect that preview may fail. If preview returns 500, see Step 6 — Preview Failure Handling. Do NOT mark the segment as deploy-ready until preview succeeds or the user explicitly overrides.
- **Template is ⏳ Pending or not in manifest:** Validate first, then preview. Both must succeed.
- **User customized DSL or wrote custom DSL:** Validate, then preview. Both must succeed.

POST to `/api/v5/segments/validate` with the final trigger expression and ad_type.

Both `keywords_and_targets` and `ads` (Product Ads) are now accepted by validate, preview, and create (verified 2026-06-09). Validate with the actual `ad_type` you'll deploy — no need to substitute `keywords` or fall back to the UI.

If validation fails: show the error, diagnose the cause, fix the syntax, and re-validate. Don't ask the user to debug DSL errors.

### Step 6 — Preview (mandatory — never skip)

POST to `/api/v5/segments/preview`. **This step is not optional.** A segment that goes to deploy without a preview has no safety net against broken triggers — the entire class of silent-match-everything bugs is only catchable here.

**Follow the data presentation standard in docs/copilot.md** for all output:

- Lead with the headline: "[N] [entities] matched — $X,XXX in [time period] spend"
- Show top 5-10 rows: entity name | $reason | $planned_action | 1-2 context metrics
- Never show internal calculation variables — only primary columns (entity, reason, action) plus relevant context
- Explain what the action means in plain English: "It would decrease bids on these keywords by 3-10% based on how far over target ACOS they are"
- Don't show internal calculation variables — only the curated columns that help the user understand what's happening and why

**Sanity checks before proceeding to deploy:**

1. **Match count plausibility.** If the count is suspiciously large (e.g., 500+ matches on a first-run negation segment, or every row in the table), assume a broken trigger until proven otherwise — usually a threshold that quietly evaluates the same way for every row. Investigate before deploying.
2. **Match count of zero.** Not always a bug — the profile may genuinely have nothing to act on. But confirm expectations: "Preview returned 0 matches. That can be real (account is clean) or a trigger bug. Want me to loosen a threshold and re-preview to confirm the trigger is doing what you expect?"
3. **Headline totals look round or zero.** `totals.cost_*` returning exactly $0.00 on a profile with known ad spend signals a query problem (wrong time period, wrong ad_type).

If the preview matches what the user intended, proceed to the DSL display (if show_work: full) and then deploy. If something looks off, stop and investigate before deploying.

In guided mode, present $reason and $planned_action as natural language descriptions, not as variable names.

Product Ads segments cannot be previewed via API. Note this clearly: "This segment works in the Merch Jar app but I can't preview it through the Copilot. I recommend checking it in the app before enabling it." For Product Ads, the deploy-as-disabled step (Step 7) is especially important — there is no preview safety net.

**Preview Failure Handling (HTTP 500 / "Failed to generate preview"):**

If preview returns HTTP 500 with `Failed to generate preview` on one of the core templates: this is a known open server-side issue (template previews currently return 500 on affected accounts). Do not silently proceed — surface it:

> "Preview came back with a server-side error on this template — that's a known issue we're tracking. I can't safely deploy without a preview. Options: (1) skip this template for now and come back to it later, (2) deploy without preview and check the segment manually in the Merch Jar app after first run (riskier), or (3) try a custom simplified trigger. What would you like to do?"

Default to option 1 unless the user has strong reasons to push through. If the user picks option 2, document the override in `user/MJ_COPILOT_LOG.md` with a clear note that this segment was deployed without preview verification.

Never default to "just deploy anyway" silently. Preview is the safety net and a failure here is information, not an obstacle to route around.

**Show Your Work — DSL Display (after preview, before deploy):**

If `Show Work: full` is set in config, output the following block immediately after the preview results and before asking for deployment confirmation:

```
Here's the segment I'm going to deploy:

**[Segment Name]**
[1-3 sentences explaining what was built and why: the core logic approach, what the key timeframes or thresholds are, what safeguards are in place. Written in plain English for the user — not a restatement of the code comments, but a genuine explanation of the design decisions.]

```dsl
[full DSL trigger — the exact code being deployed, with header comment, all let variables, all inline comments, all section dividers, and the final filter expression. Nothing stripped.]
```
```

Rules for this block:
- The DSL shown must be identical to what gets deployed. Generate the DSL first, then display it, then deploy it — never display a different version.
- In guided mode, still show the code block. The plain-English explanation above it is what guided users read first — the code is there for transparency, not as the primary communication.
- In power-user mode, the explanation can be shorter (1 sentence) since the user will read the code directly.
- The code block must use a `dsl` language hint for syntax highlighting if the interface supports it.
- Bid management segments deploy as a single `keywords_and_targets` segment (it covers both manual keywords and auto-targets) — show the DSL once.

After the DSL block, continue to Step 7 (deploy).

### Step 7 — Deploy (disabled by default)

**Every new segment creates as `"enabled": false`.** This is non-negotiable per the Deployment Safety Protocol. The pattern is two steps: create disabled, then enable on explicit confirmation (Step 8).

**Require Approval gate:** After the preview and DSL block (if show_work: full), check the `Require Approval` flag:
- `true` (default) — Stop and output: "Ready to create this as disabled. Confirm when you want me to save it." Wait for an explicit confirmation ("yes," "create it," "save it," "go") before calling the API.
- `false` — State "Saving as disabled now..." and proceed to the API call immediately.

**keywords_and_targets deployment:** Deploy bid management segments as a single segment with `"ad_type": "keywords_and_targets"` — the combined dataset covers both manual keywords and auto-targets, and the API now fully supports it on create + GET (verified 2026-06-09). The old two-segment workaround is retired. Product Ads deploy with `"ad_type": "ads"`.

On confirm, POST to `/api/v5/segments` with `"enabled": false`.

**Trigger Quality — Non-Negotiable:**

After creation, verify the deployed trigger is full and well-structured. Immediately after a successful POST, fetch the created segment with `GET /api/v5/segments/:id` and confirm the `trigger` field starts with `/*` (the opening of the header comment). If it doesn't — the trigger was minified or stripped during transit — PATCH immediately with the full template trigger (include `ad_type` and keep `enabled: false`) before reporting success to the user. Narrate this verification step out loud: "Confirming the trigger deployed with full comments..."

If a payload limit forced the trigger to be shortened, use these workarounds in order:
1. **Two-step deploy:** Create with a minimal valid trigger and `enabled: false`, then immediately PATCH with the full trigger.
2. **Browser-runtime split string (Cowork only):** If you're in Cowork and the Chrome extension is chunking large payloads, store the trigger in `window._segTrigger` in one `javascript_tool` call, reference it in the create call in the next. This workaround is browser-runtime specific; in shell runtimes, the payload size limit is the API's, not the transport's, and this doesn't help.
3. **Last resort (all runtimes):** Shorten only `$reason` string values — never remove comments, headers, or section dividers.

Never deploy a minified trigger and leave it. A trigger that looks like a wall of code with no comments is worse than not deploying — it trains users that this tool produces unreadable automation.

**Retry safety:** If a POST returns `201` but the response body is empty or unparseable, do NOT retry blindly. Instead: `GET /api/v5/segments` for the profile, search by name, and confirm the segment was actually created before retrying. Blind retries on a 201-with-empty-response create duplicates.

**Post-deploy verification for bid management:** After deploying the segment, do a `GET /api/v5/segments` and confirm the new ID appears in the list. Tell the user explicitly: "Saved as disabled — this single `keywords_and_targets` segment handles both your manual keyword bids and your auto targeting groups (close match, loose match, complements, substitutes) on the same schedule once enabled." This prevents the misunderstanding that auto targeting groups are not covered. (Bid management is ONE segment with `ad_type: keywords_and_targets`, not two — the old keywords-plus-targets split is retired; see the API reference.) If the segment doesn't appear, the create didn't land — investigate before reporting success.

**Segment object structure (create):**

```json
{
  "name": "Core: [Template Name]",
  "profile_id": "[profile_id]",
  "ad_type": "[keywords | targets | search_terms | campaigns | ads]",
  "trigger": "[full DSL trigger expression]",
  "action": "[set_bid | set_budget | create_negatives | set_state]",
  "action_params": { ... },
  "frequency": "daily",
  "enabled": false
}
```

**Action + action_params by template:**

| Template | action | action_params |
|---|---|---|
| Dynamic Bid Management | `set_bid` | `{"direction": "set-to-$", "value": "___target_bid", "source": "variable"}` |
| Adaptive Budget Management | `set_budget` | `{"direction": "set-to-$", "value": "___new_budget", "source": "variable"}` |
| Search Term Waste Elimination | `create_negatives` | `{}` |
| Product Ad Waste Elimination | `set_state` | `{"value": 2}` |
| Impression Recovery Boost | `set_bid` | `{"direction": "set-to-$", "value": "___target_bid", "source": "variable"}` |

> **Variable naming:** DSL variables use `$` prefix (`$target_bid`), but the API references them with `___` prefix (`___target_bid`). Always use `___` in `action_params.value` when `source` is `"variable"`.

**Frequency options:** the API accepts only `"daily"`, `"weekly"`, `"monthly"` on write — use `"daily"` for most templates. The UI also offers "After every data sync" and "Manually," but those cannot be set via API, and a segment already on one of those modes can't be re-saved via API without changing its frequency (known bug — see API reference). Note also that GET returns `daily` for "After every data sync" segments, so a `daily` value isn't a guarantee of a true daily schedule. For Budget Management on high-spend accounts where campaigns regularly cap intraday, note that more frequent scheduling is a feature request — daily is the highest API-settable frequency.

**On success:** Report the segment ID from the response. Append to `user/MJ_COPILOT_LOG.md`:
```
| [date] | [profile] | [segment name] | [segment ID] | [template name] | Created (disabled) |
```

Then proceed to Step 8.

**On failure:** Show the error response. Common causes: duplicate segment name (the pre-flight check should have caught this — if it didn't, the user may have created one manually between sessions; re-check via GET), invalid ad_type for the profile, malformed action_params. Fix and retry — don't leave the user stuck.

---

### Step 7 — Update Path (PATCH existing segment)

Triggered when the pre-flight check (Step 2) finds a duplicate and the user chooses to update, or when the user explicitly asks to modify an existing segment ("add X to my bid segment," "tune the threshold," "change the cooldown").

1. **Fetch the existing segment:** `GET /api/v5/segments/:id` with `profileid` header. Show the user what the current trigger and settings are (in plain English, not raw DSL unless power-user mode).
2. **Walk through the change:** What field(s) are changing? New trigger? New action_params? New schedule? Confirm scope with the user before editing anything.
3. **Settings confirmation (Step 4 equivalent):** Read back the specific change in plain English before writing the new DSL. "I'll add a Brand exclusion to the campaign filter — everything else stays the same. Sound right?"
4. **Validate and preview** the new trigger (Steps 5–6) — mandatory. A trigger change that widens the match set is especially risky; call it out explicitly.
5. **Require Approval gate** — same as Step 7 deploy path. If `Require Approval: true`, pause for explicit confirmation.
6. **PATCH the segment:** `PATCH /api/v5/segments/:id` with `profileid` header and a body including ONLY the fields that changed, plus `ad_type` (required — API returns 422 without it). Preserve the existing `enabled` state unless the user asked to change it.
7. **Verify:** GET the segment and confirm the change took effect and the trigger kept its full header comment (see Trigger Quality — Non-Negotiable above).
8. **Log it:** Append a new row to `user/MJ_COPILOT_LOG.md` using the **same Segment ID** as the original (the log is append-only and keyed on ID — the newest row for an ID is authoritative):
   ```
   | [date] | [profile] | [current segment name] | [segment ID] | [template name] | Updated: [one-line description of what changed] |
   ```
   If the update renamed the segment, use the new name in the Segment Name column and make the rename traceable in the Action column: `Updated: renamed (formerly "[old name]"); [what else changed]`. This avoids leaving two rows for the same ID that look like unrelated segments.

Do not create a new segment during an update path. If a trigger change is drastic enough that a new segment makes more sense (different `ad_type`, different `action`), surface that explicitly to the user and ask: "This change is big enough that a new segment might be cleaner than patching this one. Want to create a new segment and disable the old one, or patch this one?"

---

### Step 8 — Post-Deploy Enable Prompt

The segment is saved but disabled. This is the second explicit confirmation moment — the first was the create gate (Require Approval), the second is the enable gate.

Output:

> Segment created and saved as disabled (ID: [id]).
>
> [1-2 sentence recap: what it will do, what the preview matched, when it would next run.]
>
> Want me to enable it now, or review it in the app first?

Wait for an explicit "enable," "turn it on," "yes," "go live" — then `PATCH /api/v5/segments/:id` with `{ "enabled": true, "ad_type": "[same ad_type]" }` and confirm the segment is live. Update the log row from "Created (disabled)" to "Created + Enabled."

If the user says "keep it disabled" / "I'll enable it later in the app" / "review first" → confirm and offer: "No rush. Say 'enable [segment name]' when you're ready and I'll flip it from here. You can also enable it directly in the Merch Jar app."

If the user says "enable it" but the preview was suspicious (see Step 6 sanity checks), push back once: "Just to flag — the preview matched [N] entities, which felt high for this template. Do you want to re-preview with tighter thresholds first, or are you comfortable enabling as-is?" Accept their judgment either way.

Bid management is a single `keywords_and_targets` segment, so enabling is one action — it covers manual keywords and auto-targets together. (There is no longer a separate keywords segment and targets segment to keep in sync.)

### Step 9 — Next Steps

After deploying (whether enabled or still disabled), offer natural follow-up actions:
- "Want me to build [next recommended segment from account review]?"
- "You can monitor what this segment does using 'show my audit log' after it runs — the first results will appear after the next scheduled run"
- "If it's too aggressive, say 'tune this segment' and I can adjust the settings, or 'disable this segment' to stop it"
- "To deploy this same segment to your other accounts, say 'deploy to [profile name]' and I'll walk through it for each one"

If the user didn't come from an account review and there's no prior review in `user/MJ_COPILOT_LOG.md`, add: "If you want a full picture of what else to automate, say 'review my account' — I'll find your biggest waste areas and rank them by dollar impact."

**Multi-profile deployment:** When the user wants to deploy the same segment type to multiple profiles, walk through each profile individually: pre-flight duplicate check per profile, confirm the profile, check for profile-specific config (protected campaigns, naming conventions), validate and preview per-profile, deploy disabled with confirmation, enable prompt. Don't batch-deploy across profiles without per-profile review — settings that work for one account may not work for another.

---

## Segment Naming Convention

Use the template's collection name + a profile-specific identifier if needed. Examples:
- "Core: Dynamic Bid Management"
- "Core: Search Term Waste Elimination"

**ASCII only — strictly enforced:** Use only ASCII characters in segment names. No em-dashes (—), smart quotes (smart double and single quotes), ellipses (…), or any other Unicode characters. Use hyphens (-), colons (:), or forward slashes (/) instead. Em-dashes in particular cause API response parsing failures (the create endpoint returns 201 but with an empty body — see API reference Known limitations). Sanitize any user-supplied names before using them in the POST body.
