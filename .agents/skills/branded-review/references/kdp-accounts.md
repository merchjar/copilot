# Book (KDP) accounts

Read this when the analyzer returns `kdp`, a report has KENP columns, or the user says they advertise books. Kindle Unlimited reads earn KENP royalties that Amazon does not count as attributed sales, so standard ACoS understates what book ads return.

## Recognize a book account

| Signal | Strength | What to do |
|---|---|---|
| Search term report has KENP columns with page reads | Strong | The analyzer adds KENP figures automatically |
| Merch Jar data has KENP activity | Strong | `connected_report.py` adds KENP figures automatically |
| The user says they advertise books | Strong | Pass `--account-type kdp`, or save `"account_type": "kdp"` in the brand reference |
| Advertised ISBN-10 product IDs (10 digits, can end in X) | Weak | Result shows `kdp.status: possible`. Ask once whether they advertise books; the report is unchanged |

KENP headers vary. The analyzer matches them flexibly, for example `Estimated KENP royalties (14 days)`, `KENP Royalties`, `Kindle Edition Normalized Pages (KENP) Read (14 days)`, `KENP Read` and API-style `kindleEditionNormalizedPagesRoyalties14d`. If an export has several KENP royalty windows, pass `--kenp-royalties-column` with the window that matches the sales column. Numeric ASIN search terms alone are not a book signal: any product can show on a book's detail page. KENP columns with no page reads on an unconfirmed account are not a signal either.

## Brand reference for books

For a book account, the brand is the author. Set `--brand` to the main author name and add rules with a `kind`: `author`, `pen_name`, `series` or `title`.

```json
{"rules": [
  {"term": "mara quillon", "match": "phrase", "status": "approved", "kind": "author"},
  {"term": "saltglass chronicles", "match": "phrase", "status": "approved", "kind": "series"},
  {"term": "ember of the tidewell", "match": "phrase", "status": "approved", "kind": "title"},
  {"term": "home again", "match": "exact", "status": "proposed", "kind": "title"}],
 "competitors": [{"term": "rowan ashcombe", "match": "phrase", "status": "approved", "kind": "author"}]}
```

- Approve author names, pen names and distinctive series names after a quick check with the user.
- Approve a distinctive title. Hold a title that is an everyday phrase (“Home Again”, “The Last Summer”) as `proposed`, usually with `exact` matching, until the user decides; its spend stays in review. Title rules never use `contains_compact`.
- Collect every format's ASIN for the owned list: Kindle, paperback, hardcover, audiobook and box sets. Save it as the scoped catalog. The Advertised product report's brand field for books can be blank or show a publisher, so confirm ownership with the user instead of relying on it.
- Other authors' names that shoppers search for are competitor traffic. Add only names the user confirms to `competitors`. They stay in non-branded, labeled `Confirmed competitor author`, with a `competitor_queries` subtotal. Do not infer which queries are author names; you can show a few high-spend non-branded queries and ask.

## KENP in the report

- Standard ACoS stays the headline and is unchanged: spend / attributed sales.
- ACoS incl. KENP = spend / (attributed sales + estimated KENP royalties), shown for branded, non-branded and overall. The analyzer computes it; never estimate it yourself.
- Uploaded reports use the report's estimated KENP royalties, with Sales as the sales basis.
- Merch Jar data uses adjusted sales and adjusted estimated royalties, which apply the account's Ad Impact Multipliers. The report states any multiplier other than 1 (for example KENP royalties x1.25). If adjusted fields are missing, it falls back to reported values and says so. Repeat that disclosure in chat.
- Royalties reconcile across classes like spend and sales. The source total must match.
- KENP royalties are Amazon estimates, and recent periods can change. Royalties are earnings, not list-price sales, so describe ACoS incl. KENP as a fuller return view, not profit.
- Merch Jar's Blended metrics (blended profit, blended ACoS) are profit-margin views. Do not headline them in this report; one brief mention that Merch Jar offers them is enough.

In chat, add one line after the standard ACoS figures: “Including KENP royalties: branded X%, non-branded Y%, overall Z%.” Natural requests to expect: “I advertise books.” “Add my pen name.” “Rowan Ashcombe is another author.”
