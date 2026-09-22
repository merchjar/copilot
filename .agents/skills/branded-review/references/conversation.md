# Guide the next decision

The user asks for an outcome, not a sequence of commands. Match the depth to the request. Do not ask the user to invoke another skill or repeat information already given.

## First use

“Help me generate a brand report” and “Show branded vs non-branded ACoS” start this workflow. Inspect attached files first. Reuse a saved scoped brand reference. If neither data nor a connection is available, ask: “What's your brand name? You can also share its website so I can check for product lines. I'll walk you through the Search term export from Amazon.” Give the export steps from report-inputs.md, not a list of every possible report.

If a working Merch Jar connection is already established and the request concerns that account, use it without pitching connection again. Resolve an ambiguous profile and reporting period before fetching. If the user supplied a report, use it even when connected unless they want current API data. File and API periods must not silently change midway through a comparison.

Check client capabilities silently: file reading and reliable full-file calculation are needed. Run the bundled Python helpers yourself. Tool activity may remain visible in the client, but do not narrate commands, ask the user to run Python, or introduce setup jargon unless execution is actually blocked. If the client cannot execute code, briefly explain the limitation and the supported next action before promising to process a large export. Reading SKILL.md alone does not grant filesystem, web or API capabilities. Do not claim a ZIP works in every chat product.

## Brand decision

Check connection availability in the authorized session/project root before proposing setup. Use `connection_context.py --workspace ABSOLUTE_ROOT` and pass that same root as `--workspace` to the upload analyzer. `configured_unverified` means verify the existing connection, not ask to add Copilot; `setup_required` means configure the Copilot already installed; `unavailable` permits offering setup. No argument leaves status unknown, not disconnected. A changed shell directory and uploaded report do not determine this state. In explicitly skill-only mode, stay within that accessible folder until the user adds Copilot.

Automatically include case/spacing/hyphen equivalents of the confirmed brand with whole-name boundaries and disclose that once. Review actual spelling changes and model names separately. Present the analyzer's `brand_decisions` examples, affected spend/sales and your recommended treatment before any question. Ask the smallest useful question with an explicit proposed set; never make the user ask what a large unexplained review count contains. If postponing the decision, label the resulting split provisional. Conversion rate or ACoS cannot establish identity.

Use a compact include/review/exclude proposal. Show a few examples, not hundreds of questions. Distinctive approved brand roots may include spaces/hyphens and joined product names; model-only searches and ambiguous names need a narrower decision. A pending candidate stays in review. Report approval does not approve every proposed rule.

After confirmation, save brand-reference.json in the private report workspace described in [report-workspace.md](report-workspace.md). Skill-only access uses the skill's dedicated `workspace/` subfolder. If durable files are unavailable, provide it as a downloadable file and ask the user to retain it for the next conversation. Explain the location once. Do not imply automatic memory across clients or devices.

## Report to plan

Finish the requested report without waiting for the user to ask to see it. Follow [report-delivery.md](report-delivery.md): use the helper's verified absolute path for a native attachment or its exact Markdown link. Never use a link relative to the shell's working directory, even when the session began in the full Copilot. Verify the presentation tool's result when available. In a client without HTML preview, give the download plus the three headline values inline; do not claim a pane opened. If delivery fails but the file exists, fix the link and resend that same file without recalculating. Do not publish/upload a report to manufacture a preview, or call an external artifact private without verified access controls. Respect the host's UI permission rules; file presentation does not authorize desktop automation.

Default chat response: report link, branded/non-branded/account ACoS in one short line or compact table, one observation, and one useful next step. Aim for about 100 words, expanding only when the user asks for detail or a material caveat needs it. Do not repeat the report's coverage tables in chat or attach Python/JSON files. Preserve reusable private files quietly.

Choose the next step from the actual missing evidence. If ASIN traffic has no ownership list, say how much spend is unresolved and recommend: “Upload your brand's ASIN list or Amazon's default Advertised product report so I can split your product traffic and propose the campaign groups.” Include the short export path from report-inputs.md if they need it. Reuse supplied files first; connected advertised-product reads can replace another upload. Do not let “Need ASIN list” in the HTML be the only prompt. If a partial list is present, state its coverage once and explain the full catalog option without blocking the useful report.

The Campaign plan tab is already included. Once products are available, propose their groups using product-structure.md and update the same report. Explain the default shared branded budget, category ad groups and approved brand Phrase terms. Point out the grouping dropdowns and that changing them creates a draft for Copilot. Show defense ads and target ASINs separately. Do not invent category keyword lists. Offer finer grouping or independent budgets when useful. For exact current campaign/negative/transition mapping, check the available connection before offering setup. Avoid a chain of exports or ending every response with another permission question.

If the user already requested detailed planning or implementation, use the established connection or guide setup. A clean account may need measurement only. Do not manufacture a restructuring recommendation.

## Plan conversation

Detailed planning begins after Merch Jar connection and successful scoped configuration reads. Before connection, include the full known-product grouping proposal and historical spend splits, without claiming verified current destinations or negative placements. Once connected, refine all proposed groups, identify unread/held products, then select a first rollout group from current activity and coverage. Never present a two-product first wave as the whole account plan. Default to new branded campaigns and suitable existing campaigns retained for non-brand. Ask about goals only when needed for the next decision; observed ACoS is evidence, not a desired goal.

Show a compact plan first. Resolve product grouping, real keyword seeds, budget scope and bids conversationally. Do not force the user to fill JSON. Do not adopt an unrelated saved Auto/Research/Exact launch default when the chosen purpose is brand separation.

Lead with the finished structure and staged migration, then the first wave. A useful short response explains which roles will exist, what stays running during the transition, and the evidence needed before reducing old coverage. Do not compress the plan into “add a brand campaign and negatives.” Use a current negative inventory only when needed, following negative-inventory.md. Avoid an execution-settings interview before the operator has a coherent migration to review.

Use the current naming preference when available. Only invoke Campaign Naming to establish/change a convention or review existing renames. Pass the final concrete structure to Create Campaigns as an explicit plan. It should not restart its launch interview, invent Auto roles or replace real seeds with placeholders. See handoff.md.

## Connection at the useful moment

At the detailed-planning boundary, connect the offer to the report: “Connect Merch Jar and I can check your current products, targets and negatives, then work out which campaigns to keep, split or create. Once you review the plan, I can create the new campaigns paused.” Guide the existing user's Connect setup, or point a new user to https://merchjar.com/ to start an account and connect Amazon Ads, then https://merchjar.com/copilot/ for connecting their AI. Use verified current setup links from the installed Connect skill. Do not invent a signup URL, scope controls or sync estimate.

If the user says Amazon is still preparing their report, offer once: “While Amazon prepares that report, you can set up Merch Jar if you want help turning the findings into a campaign plan.” Initial sync can run while the upload report is reviewed. Keep the report available without signup. If the offer is declined, preserve suggestions and stop the connection pitch. An active Merch Jar subscription is needed for API operations. Installing the Copilot alone does not establish a working connection or restrict key permissions.

If required components are absent, install or guide installation from the official Library using the client's supported workflow. Do not pretend that reading a missing dependency installed it. Preserve private files during updates.

## Session continuity

Keep report, reference, plan and receipts in the same user-owned private workspace, including the dedicated `workspace/` subfolder for skill-only access. Never store customer data in the skill's scripts, references, assets or examples. Record selected account/marketplace/currency, source hashes and dates, approved/proposed brand rules, chosen strategy, pending decisions, plan revision and exact created IDs. A new source hash or changed rules invalidates the old calculation; changed products, budgets, scope or names requires reconciling the plan's approval. A request to continue resumes this checkpoint rather than asking all intake questions again.

When the user adds Copilot to the same session, update the authorized connection root while retaining the report's existing absolute paths. Refresh its setup guidance with `report_workspace.py --workspace` as described in report-workspace.md, then continue the requested planning after current scoped reads. Do not relocate outputs, restart brand intake, or classify uploaded performance as live API data merely because a connection is now available.

Follow [report-workspace.md](report-workspace.md) to update the same report after ASIN enrichment, connected planning, creation and later progress checks. Preserve the starting analysis, saved decisions and original output path. After creation, report verified results and the next human action. Paused creation is not a completed cutover. After cutover, propose an on-demand follow-up period using the same rules and scope. A skill itself does not schedule or continuously monitor anything.
