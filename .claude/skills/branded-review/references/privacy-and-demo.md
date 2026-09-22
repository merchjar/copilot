# Private presentations and separate demo accounts

## Privacy report

When the user asks for privacy mode, make a separate presentation file. Run this agent-side command on the saved analysis:

```text
python scripts/privacy_report.py --analysis PRIVATE/analysis.json --html-output OUTPUT/brand-review-private.html
```

The helper builds the presentation from allowed numeric fields and fixed labels. It removes account/brand/product/campaign/ad-group names, terms, ASINs, IDs, URLs, source paths, hashes and exact dates, including the collapsed details and HTML title. It preserves original metrics and marks that visibly. It does not copy raw rows, private notes or future arbitrary metadata into the HTML. It never overwrites an existing file; choose a separate neutral output filename.

This is identity redaction, not a guarantee of anonymity: exact financial results and counts remain. For a recording that must not expose a real client's figures, use the fictional sample files. Do not claim this mode sanitizes earlier chat, file attachments, original analysis, browser tabs or local folder names. Show only the sanitized presentation, or begin a fresh sample conversation. Do not attach the private analysis or brand reference with it.

Continue analysis against the original private evidence; never reuse the redacted report as an execution manifest or replace the original report with it. Generating a private presentation does not authorize publishing customer data.

## Analysis access and implementation access

For a recording walkthrough, generate a separate anonymized report with selectable simulated progress scenes:

```text
python scripts/demo_walkthrough.py --analysis PRIVATE/analysis.json --html-output OUTPUT/demo-walkthrough.html
```

This preserves the input's performance and campaign distribution, replaces identifying names, terms, ASINs and IDs with a fictional brand, and shifts dates. All three report tabs use the production renderer. Setup scenes exercise the real progress display, including paused campaigns, no impressions, separate defense readiness and stale data. Their evidence is fictional and stays inside the presentation. It is never saved into real progress files or accepted by the preference importer. No account calls occur. Use a new output path; the helper preserves existing files. Review the generated HTML before recording. Exact figures remain, so this is not a guarantee that financial data cannot be recognized.

The standalone download includes generator code and fictional sample inputs only. Never package a customer-derived walkthrough or its private mapping with the skill.

Uploaded files alone require no API key. Protect source files by reading them and writing outputs elsewhere. If live source-account data is needed, use credentials with read-only scopes and a restricted account selection where the service supports that. A prompt saying “read only,” a folder boundary or a hidden skill is not a credential permission boundary. Verify the actual available scopes and account access; do not promise profile restriction unless supported and configured.

For a two-part demonstration, keep the upload-only report workspace separate from the connected demo workspace. The second contains the toolkit and private demo credentials, with no source-account reports or credentials. Private key entry is through Connect's supported local configuration, never a chat message or a recorded screen.

Carry across the structural idea only. Explicitly identify the switch to a demonstration account. Use that account's own products, marketplace, currency, names and realistic seeds. Never substitute a profile ID into a real client's manifest or send their ASINs to another account. A real paused creation still needs the exact reviewed plan and authorization; verify objects and states before saying they were created.

If no account changes are authorized, show a proposed plan or an explicitly labeled simulation. A simulation must not use fake IDs, receipts or success messages presented as actual creation. The customer's account remains untouched in either path.
