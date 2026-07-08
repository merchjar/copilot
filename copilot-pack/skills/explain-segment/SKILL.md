---
name: explain-segment
description: Explain what a segment does in plain English. Use when the user asks "explain this segment," "what does this do," "translate this to English," "break this down for me," "help me understand this," or pastes segment code and seems to want to understand it rather than edit or deploy it. Also use when a non-technical user wants to understand a segment that someone else built.
---

# Explain Segment Skill

## Context to Load Before Starting

1. `reference/V2_SYNTAX_REFERENCE.md` — for parsing DSL
2. `reference/MJ_API_REFERENCE.md` — only if the user provides a segment ID instead of pasting DSL (needed to fetch the segment)

Do NOT load creation guidelines or templates — this skill explains, it doesn't create or deploy.

---

## Overview

Parse a segment and explain it in plain English — what it does, when it acts, what it protects against, and what the user can adjust. No DSL jargon. Use advertising analogies.

---

## Workflow

### Step 1 — Receive the Segment

User pastes DSL or provides a segment ID. If ID, fetch via API (load `reference/MJ_API_REFERENCE.md` first).

### Step 2 — Parse Structure

Identify the main sections:
- Header (name, version, purpose)
- Core Settings (the dials users control)
- Logic (what decisions the segment makes)
- Diagnostics ($reason, $planned_action)
- Final Filter (what entities actually get acted on)

### Step 3 — Explain in Plain English

Work through the segment in four parts:

**What it does (one sentence):**
"This segment looks at all your active keywords and adjusts bids based on how efficient they are relative to your ACOS target."

**How it decides to act:**
Explain the core logic flow without DSL. Use advertising analogies, concrete examples with real-looking numbers.
- "It looks at performance over the last 7 days if you have enough data, then falls back to 14 days, then 30 days — so newer accounts with less data still get bid adjustments."
- "It won't change bids if your ACOS is within 10% of target in either direction — that's the 'leave it alone' zone."
- "The further your ACOS is from target, the bigger the change — but never more than 10% in either direction."

**What it protects:**
- "It won't make changes more often than once every 2 days — that's the cooldown. Changing bids too often doesn't give Amazon's algorithm time to adjust."
- "There's a maximum bid based on your average cost-per-click — so it won't let bids run away even for great keywords."

**What you can control (settings reference card):**
List every user-adjustable setting (the Core and Strategy sections), the current value, and what changing it would do.

| Setting | Current value | What it does |
|---|---|---|
| Minimum orders for evaluation | 2 orders | Won't adjust bids until a keyword has at least 2 orders — prevents acting on noisy data |
| Minimum bid change | 3% | The smallest change it'll make. If a tiny adjustment is warranted, it'll still move at least 3% |
| Maximum bid change | 10% | Never adjusts more than 10% in one run — keeps changes gradual |
| [etc.] | | |

### Step 4 — Offer Next Steps

After explaining, offer:
- "Want me to change any of these settings?"
- "Want to preview what this would do to your account right now?"
- "Want to understand any part of this in more detail?"

---

## Tone Guidelines

- No DSL terms in explanations. Say "it waits 2 days before adjusting again" not "the cooldown_period is set to 2d."
- Use concrete numbers from the segment's actual settings, not abstract descriptions
- Advertising analogies: "like a thermostat" for bid management, "like a blacklist" for protected terms, "like a waiting period" for cooldowns
- Always explain the *why* behind a design choice, not just the *what*: "The cooldown exists because Amazon's algorithm needs time to respond to bid changes — touching it every day would be like adjusting your thermostat every 5 minutes"
