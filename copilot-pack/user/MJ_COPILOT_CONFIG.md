# Merch Jar Copilot Config

<!-- MACHINE-READ: The "## " headings in this file are parse anchors for the API client
     (tools/merchjar_client.py reads the key from under "## API Key"). Do not rename,
     translate, or reorder these headings, or the client will not find your key. -->

## Config Version
3

## API Key
<!-- Paste your API key here as a BARE line: just the key, on its own line, directly under this heading. -->
<!-- Correct:   mj_live_xxxxxxxxxxxxxxxxxxxxxxxx -->
<!-- Do NOT wrap it in backticks, quotes, a "- " list marker, or a "Key:" label, and do not indent it. -->
<!-- Easiest path: paste your key into the chat and the Copilot saves it here in the right format automatically. -->
<!-- In Cowork: you may need to say "this is my Merch Jar API key" when pasting, -->
<!-- because Cowork flags raw mj_live_... tokens as potential accidental credential pastes. -->

## Profile IDs
<!-- Auto-populated when you connect your API key. -->
<!-- Ask the Copilot to "refresh my ad accounts" to pick up new accounts. -->

## Preferences
<!-- Account-wide settings. Customized during setup or anytime you say "update my preferences". -->

Privacy Mode: off
<!-- Options: off | on -->
<!-- "on" — Masks account names, campaign names, ad groups, ASINs, and product titles in all output. -->
<!--        Dollar amounts, percentages, counts, search terms, keywords, and DSL code are never masked. -->
<!--        Use for screen recordings, demos, or any content shared publicly. -->
<!-- "off" — Default. Real account data shown as-is. -->

Show Work: off
<!-- Options: off | full -->
<!-- "full" — Copilot outputs the complete Segment DSL in chat before deploying. -->
<!-- "off" — Default. Code is visible in the Merch Jar app after deployment, not in chat. -->
<!--          (On the first build of a session the Copilot shows the DSL once anyway, so you can -->
<!--           see what it deployed; say "show your work" to see it on every build.) -->

Require Approval: true
<!-- Options: true | false -->
<!-- "true" — Default. Copilot pauses and waits for explicit confirmation before deploying any segment. -->
<!-- "false" — Copilot deploys after showing the summary. Reserved for demos and power users. -->
<!-- This default exists because Segments can take irreversible account actions on their first run. -->

Automation Style: conservative
<!-- Options: conservative | moderate | aggressive -->
<!-- Sets default thresholds for all segment builds: -->
<!--   conservative — Larger safety margins, tighter data requirements, smaller bid/budget changes (default) -->
<!--   moderate — Standard thresholds from templates as-is -->
<!--   aggressive — Looser data requirements, larger changes, faster reaction to signals -->
<!-- You can always override individual settings during a build. This sets the starting point. -->

Default ACOS Target:
<!-- Optional override. If set, the Copilot uses this instead of your Merch Jar account-level Target ACOS. -->
<!-- Leave blank to use the Target ACOS from your account settings (pulled from API each session). -->
<!-- Format: number without % sign. Example: 30 -->

Account Type:
<!-- Options: brand | agency | kdp -->
<!-- Helps the Copilot calibrate recommendations and language: -->
<!--   brand — Single brand, focused on ROAS and efficiency -->
<!--   agency — Multiple brands/profiles, portfolio-level workflows -->
<!--   kdp — KDP/Merch on Demand, royalty-based margin structure -->
<!-- Leave blank and the Copilot will infer from your profile setup. -->

Segment Naming Prefix: Core
<!-- Prefix for new segment names. Default: "Core" (e.g., "Core: Dynamic Bid Management"). -->
<!-- Agencies often set this per-profile in Profile Context below. -->

Default Profile:
<!-- Profile name or ID to load automatically when you don't specify one. -->
<!-- Leave blank to be asked each time (recommended for multi-profile accounts). -->

## Protected Items
<!-- Account-wide protection rules. Applied to all profiles unless overridden in Profile Context. -->

Protected Terms:
<!-- Comma-separated. Search terms that should never be negated. Typically brand names and core product terms. -->
<!-- Example: merch jar, merchjar, my brand name -->

Protected Keywords:
<!-- Comma-separated. Keywords to exclude from bid automation. Typically branded terms with manually-tuned bids. -->
<!-- Example: merch jar exact, brand keyword phrase -->

Excluded Campaigns:
<!-- Comma-separated campaign name patterns to exclude from all automation. Supports partial matches. -->
<!-- Example: Test, Legacy, Do Not Touch -->

## Profile Context
<!-- Per-profile notes and overrides. The Copilot reads these when working on a specific profile. -->
<!-- Add context manually or say "remember that [profile] is..." during a session. -->
<!-- The Copilot may suggest adding context when it learns something useful — it always asks first. -->

<!-- TEMPLATE (copy for each profile after connecting):
### [Profile Name]
Category:
Target ACOS Override:
Naming Prefix:
Protected Terms:
Notes:
-->

## Notes
- The `user/` folder is yours — it survives version upgrades
- Never commit `user/` to version control; it contains your API key and account data
- Never share your API key publicly
- Say "update my preferences" or "help" anytime
