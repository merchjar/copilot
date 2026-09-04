# Property sets

Custom-property schemas the Library's skills and templates rely on (Merch Jar calls
them custom fields in the API: `cf_*` keys, `custom.cf_*` in Segment logic). A
property set is a folder with `property-set.json` (definitions + optional CSV import
mapping) and a short README. Applied by the `enrich-account` skill; read by any
template that lists it under `Requires-Properties:`.

```json
{
  "id": "brand",
  "name": "Brand classification",
  "version": "1.0",
  "description": "Tags targets and search-term sources as branded / non-branded / competitor.",
  "entity_types": ["targets", "campaigns"],
  "fields": [
    {"key": "cf_brand_type", "type": "select", "options": ["branded", "nonbranded", "competitor"], "description": "..."},
    {"key": "cf_brand_reason", "type": "text", "description": "why the classifier chose that value"}
  ],
  "import": {"csv_columns": {"Campaign Name": "campaign_name", "Brand Type": "cf_brand_type"}},
  "pairs_with": ["branded-review"],
  "goal": "protect",
  "last_updated": "2026-09-04"
}
```

None ship yet; the first sets (brand, protect, economics, backup, experiment) land with
the skills that use them.
