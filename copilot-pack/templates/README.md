# Segment Templates

Validated, ready-to-deploy automation Segments for Amazon Sponsored Products. Each
template is a Merch Jar Segment (the DSL that runs your automation), written to be
previewed before it changes anything and deployed disabled by default.

The Copilot reads these templates to recommend, explain, and deploy automation on
your account. You can also open any template directly to see the exact logic.

## The core library

| Template | Dataset | What it does |
|---|---|---|
| `core-search-term-waste-elimination.txt` | Search Terms | Negates wasteful search terms using efficiency targets and performance analysis. |
| `core-dynamic-bid-management.txt` | Keywords & Targets | Adjusts bids proportionally to how far ACOS is from target, with CPC-based caps and adaptive cooldowns. |
| `core-adaptive-budget-management.txt` | Campaigns | Prevents budget waste while keeping enough spend for data collection and scaling. |
| `core-impression-recovery-boost.txt` | Keywords & Targets | Raises bids for proven performers when impression volume drops. |
| `core-product-ad-waste-elimination.txt` | Product Ads | Pauses product ads that have spent enough without efficient results. |

## How templates are structured

Every template opens with a header comment that carries its name, version, dataset,
recommended action, and categorization tags. The settings below the header are
grouped into `CORE` (safety mechanics), `STRATEGY` (thresholds you tune), and `TIME`
(lookback windows and cooldowns). Every setting has an inline comment explaining what
it does, so you can read and adjust the logic yourself.

## The manifest

`manifest.json` at the repo root is the generated catalog of every template: id,
name, path, tags, description, and last-updated date. The Copilot fetches it to list
the library, filter by tag, and check for updates. It is generated from the template
headers, never hand-edited.

## Deploy safety

Templates are always previewed against your real account before they change anything,
and deploy disabled by default so you can review before turning them on. The Copilot
walks you through preview and confirmation on every build.
