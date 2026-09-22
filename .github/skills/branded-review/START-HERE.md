# Brand Traffic Review

Compare branded and non-branded advertising performance, then plan how to give each group its own goals and targeting.

## Start

Use an AI client with file access and code execution. Extract the whole `branded-review` folder, including scripts, references and assets. Install it using your client's skill installation workflow, or open the folder as part of a project and ask the AI to read `SKILL.md`. The AI runs the included calculations for you. You don't need to write code. The helpers require Python 3.9 or later in the client's execution environment.

For Codex, the project skill location is `.agents/skills/branded-review/`. Put the complete folder there. Codex can select it from a matching request, or you can invoke `$branded-review`. [Official skill documentation](https://learn.chatgpt.com/docs/build-skills).

Start with:

> Help me generate a brand report.

Share your brand name, an optional website URL, and an Amazon Search term report if you have one. The skill will guide the export if you need it. You don't need Merch Jar for the report or structural suggestions.

It will ask you to review what counts as branded and present a report you can open or download, with suggestions for separating goals and targeting. To move into a detailed campaign plan, connect Merch Jar and say:

> Help me separate branded and non-branded campaigns.

With Merch Jar connected, the skill checks your current products, targets and negatives before working out which campaigns to keep, split or create. The plan shows how to transition one product group at a time while retaining useful discovery and existing coverage. You won't need to download bulk-operation sheets.

Your saved brand rules, report and plan stay in a private workspace. If you open only the skill folder, the AI uses its `workspace/` subfolder. Adding the full Copilot later continues with those same files. Keep that workspace when updating or replacing the skill. Local files are shared only with clients using those same files.

The report includes Performance, Campaign plan and Setup & progress tabs. It prompts you to add an ASIN list or Amazon's Advertised product report when ownership data is missing. Product names help it suggest related groups in a shared branded campaign, with separate own-product defense. Use the dropdowns to compare budgets and product groupings. Inspect the keywords or ASINs being targeted beside the products being advertised. Copy your choices or save them in a report copy for Copilot to update the plan. The proposal covers your known products before choosing a first rollout group.

Open **Your brand lists** to review or edit names and ASINs. Use **Copy changes for Copilot**, or attach the saved report with changes, and ask it to update the report. The AI checks the edits and saves your preferences before recalculating. Browser edits alone do not change your ads. Setup & progress shows existing campaigns, proposed coverage and the next actions, using saved account checks when available.

For a presentation, ask: “Make a privacy copy of the report.” It hides identifying text and dates in a separate file while preserving the figures. Earlier chat and uploaded files remain unchanged. Use the fictional sample below when you also need to keep a client's financial results private.

## Connected work

Merch Jar connection is required for the detailed campaign, negative and transition plan. After you review that plan, the skill can use Create Campaigns to stage approved new objects paused. Enabling and changing existing campaign exclusions are separate steps shown in the plan.

If you don't have an account, start at [Merch Jar](https://merchjar.com/) and connect your Amazon Ads account, then follow [the Copilot setup](https://merchjar.com/copilot/) to connect your AI. You can start setup while Amazon prepares your report. The skill checks data availability before planning; your upload report can proceed while initial sync is pending.

Use Merch Jar Connect 1.5 or later and Create Campaigns 1.3 or later. Campaign Naming 0.4.0 or later helps choose or change a naming convention; an existing convention can be reused without that optional skill. Get current components from the [Merch Jar Library](https://merchjar.com/library/). An active Merch Jar account is required for connected operations.

The skill cannot add file execution or network access to a chat client that lacks those capabilities. AI-client costs and account permissions are separate from this free download.

## Try the sample

The files in `examples/` contain a fictional Northstar Gear account. They are sample input for the skill, not a template customers have to fill out. Ask:

> Use the sample files to show me how this works.

The sample's approved name is Northstar Gear. Expected results: 10% branded ACoS, 40% non-branded ACoS and 21.2% across the supplied report. Product and blank-query spend remain outside the text split.

This download makes no automatic account changes and sends no telemetry. Review the generated report before sharing account data.
