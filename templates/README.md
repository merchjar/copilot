# Segment Template Library

The master library of validated, ready-to-deploy automation Segments for Amazon
Sponsored Products. Templates are organized by category and grow over time. This
is the canonical home for every template, and the Copilot fetches from here on
demand.

Merch Jar Segments are written in the DSL that runs your automation, built to be
previewed before they change anything and deployed disabled by default.

## Categories

- `core/` foundational automations. These are also deployed to every Merch Jar
  account by the app, so the Copilot Pack does not bundle them.
- `defensive/` waste elimination and guardrails.
- `harvesting/` finding and scaling proven performers.
- `branded/` branded-term strategy.

More categories are added as the library grows.

## The core library

| Template | Dataset | What it does |
|---|---|---|
| `core/core-search-term-waste-elimination.txt` | Search Terms | Negates wasteful search terms using efficiency targets and performance analysis. |
| `core/core-dynamic-bid-management.txt` | Keywords & Targets | Adjusts bids proportionally to how far ACOS is from target, with CPC-based caps and adaptive cooldowns. |
| `core/core-adaptive-budget-management.txt` | Campaigns | Prevents budget waste while keeping enough spend for data collection and scaling. |
| `core/core-impression-recovery-boost.txt` | Keywords & Targets | Raises bids for proven performers when impression volume drops. |
| `core/core-product-ad-waste-elimination.txt` | Product Ads | Pauses product ads that have spent enough without efficient results. |

## How templates are structured

Every template opens with a header comment that carries its name, version,
dataset, recommended action, and categorization tags. The settings below the
header are grouped into `CORE` (safety mechanics), `STRATEGY` (thresholds you
tune), and `TIME` (lookback windows and cooldowns). Every setting has an inline
comment explaining what it does, so you can read and adjust the logic yourself.

## The manifest

`manifest.json` at the repo root is the generated catalog of every template: id,
name, path, category, tags, description, and last-updated date. The Copilot
fetches it to list the library, filter by tag, and check for updates. It is
generated from the template headers by `tools/build_manifest.py`, never
hand-edited.

## Deploy safety

Templates are always previewed against your real account before they change
anything, and deploy disabled by default so you can review before turning them
on. The Copilot walks you through preview and confirmation on every build.
