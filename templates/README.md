# Segment Template Library

The master library of validated, ready-to-deploy automation Segments for Amazon
Sponsored Products. Templates are organized into three category folders and grow
over time. This is the canonical home for every template, and the Copilot fetches
from here on demand.

Merch Jar Segments are written in the DSL that runs your automation, built to be
previewed before they change anything and deployed disabled by default.

## Category folders

Every template lives in exactly one folder, keyed on what it does to the account:

- `optimize/` takes an action — adjusts bids or budgets, negates search terms,
  pauses waste, harvests performers. The five account defaults live here.
- `insight/` surfaces information and takes no action — diagnostics and
  investigation tools.
- `utility/` setup and housekeeping.

Everything finer-grained than the folder is a **tag** in the template header
(see below), not a folder. Notably, `default` is a tag: the five automations the
app deploys to every account are `optimize/` templates tagged `default`, so the
Copilot recognizes "already on the account" by name/header plus that tag.

## The account defaults

These five `optimize/` templates are tagged `default` and are cloned (disabled)
onto every Merch Jar account by the app, so the Copilot Pack does not bundle them:

| Template | Dataset | What it does |
|---|---|---|
| `optimize/core-search-term-waste-elimination.txt` | Search Terms | Negates wasteful search terms using efficiency targets and performance analysis. |
| `optimize/core-dynamic-bid-management.txt` | Keywords & Targets | Adjusts bids proportionally to how far ACOS is from target, with CPC-based caps and adaptive cooldowns. |
| `optimize/core-adaptive-budget-management.txt` | Campaigns | Prevents budget waste while keeping enough spend for data collection and scaling. |
| `optimize/core-impression-recovery-boost.txt` | Keywords & Targets | Raises bids for proven performers when impression volume drops. |
| `optimize/core-product-ad-waste-elimination.txt` | Product Ads | Pauses product ads that have spent enough without efficient results. |

## How templates are structured

Every template opens with a header comment that carries its name, version,
dataset, recommended action, and categorization tags. Tags are the fine-grained
vocabulary (`default`, `bid`, `budget`, `waste`, `negation`, `harvesting`,
`find-opportunities`, `one-off`/`ongoing`, `kdp`, `seasonal`, `recommended`, and
more), shared with the Webflow tags so both surfaces speak one language. The
settings below the heade