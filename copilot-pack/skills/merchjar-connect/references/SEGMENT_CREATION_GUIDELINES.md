# Segment Creation Guidelines v1.1

## Purpose

Standards and patterns for creating Merch Jar automation segments. Use alongside `V2_SYNTAX_REFERENCE.md` for syntax validation.

**Target audience:** Established Amazon advertisers — brands, aggregators, and agencies managing significant ad spend. Segments should assume users care about both control and scale, and are willing to trade simplicity for robust, reliable logic.

---

## Design Philosophy

**Consolidate use cases.** Handle multiple scenarios in one segment when possible:
- Same dataset + compatible logic → consolidate
- Different datasets or conflicting safeguards → separate
- User wants selective deployment → separate

**Use calculated target values over percentage adjustments:**
- Better: `Change Bid: Set ($) using $target_bid` where `$target_bid` is calculated
- Avoid: `Change Bid: Increase (%) using $percentage_change` with positive/negative values

This provides cleaner logic, more precise control, and easier debugging.

---

## Required Header Format

Every segment must include a header comment:

```
/*
=== [Collection]: [Segment Name] ===
Version: [X.X]
Docs: merchjar.com/templates?t=[slug]

Purpose: [One sentence description - max 20 words]
Dataset: [Dataset name]
Recommended: [Action Type] | [Schedule]
*/
```

**Slug generation:** Lowercase name with hyphens for spaces, colons removed.
- "Seasonal Bid Tuner" → `seasonal-bid-tuner`
- "KDP Core: Product Ad Waste Elimination" → `kdp-core-product-ad-waste-elimination`

**Versioning:**
- Minor (1.1): New features, path changes, setting additions, behavior modifications
- Major (2.0): Breaking changes, fundamental logic rewrites, removed settings

Version must match the header, CMS Version field, and Logs tab entries.

---

## Dataset Selection

**Default: Keywords & Targets** — covers both manual keywords and product/auto targets. Use for all bid management segments unless there's a specific reason not to.

| Dataset | When to use |
|---|---|
| Keywords & Targets | Bid management (default) |
| Campaigns | Budget management, campaign-level state changes |
| Ad Groups | Default bid management, ad group organization |
| Keywords | Legacy compatibility or keyword-specific strategies (rare) |
| Targets | Product/auto-specific optimizations (rare) |
| Search Terms | Negative keyword automation, search term harvesting |
| Product Ads | Individual ad performance optimization, ad-level state management |

---

## Variable Naming Standards

### Core Pattern
`[metric]_[purpose]_[context]_[qualifier]`

### Target ACOS Variables
Pattern: `t_acos_[purpose]_[context]_[qualifier]`

```
let $t_acos_threshold_increase = 80%;   // STRATEGY: Increase bids when ACOS <= (Target ACOS × 80%) [e.g., 30% target = 24% threshold]
let $t_acos_buffer = 10%;               // CORE: No-change buffer around target ACOS (Target ACOS ± 10%) [e.g., 30% target = 27-33% no-change zone]
let $t_acos_threshold_pause = 300%;     // STRATEGY: Pause when ACOS >= (Target ACOS × 300%) [e.g., 30% target = 90% threshold]
```

### Standard Variable Patterns

**Data reliability:**
```
let $orders_min = 2;            // CORE: Minimum orders needed for reliable ACOS data
let $orders_min_for_acos = 5;   // ADVANCED: Orders required for advanced ACOS evaluation
let $clicks_min = 20;           // CORE: Minimum clicks required for evaluation
let $spend_min = 5.00;          // CORE: Minimum lifetime spend threshold ($5.00 threshold)
```

**Bid adjustments:**
```
let $bid_min_change = 3%;       // STRATEGY: Minimum bid change when adjustment is warranted
let $bid_max_change = 10%;      // STRATEGY: Maximum bid change regardless of performance gap
```

**Time controls:**
```
let $cooldown_period = 2d;      // TIME: Wait 2 days after bid change before adjusting again
let $cooldown_recent = 1d;      // TIME: Short cooldown for high-confidence scenarios
let $cooldown_extended = 7d;    // TIME: Extended cooldown for volatile keywords
```

**Multipliers:**
```
let $cpc_multiplier = 2.0;          // ADVANCED: Max bid = Avg CPC × 2.0 [e.g., $0.50 CPC = $1.00 max]
let $budget_multiplier = 1.2;       // STRATEGY: Budget scaling factor (20% increase)
```

**CPC-based limits:**
```
let $bid_limit_cpc_multiplier = 2.0;    // SAFEGUARD: Max bid = Avg CPC × 2.0 [e.g., $0.50 CPC = $1.00 max]
let $bid_limit_cpc_period = 90d;        // SAFEGUARD: Period for calculating CPC-based bid limits
```

### Time Period Variables

Use role-based names. Only define periods actually used in the logic.

**Two periods:**
```
let $period_recent = 0d..7d;        // TIME: Recent evaluation period
let $period_baseline = 0d..30d;     // TIME: Baseline comparison period
```

**Three or more periods:**
```
let $period_short = 0d..7d;         // TIME: Primary evaluation period (7 days including today)
let $period_medium = 0d..14d;       // TIME: Secondary evaluation period (14 days including today)
let $period_long = 0d..30d;         // TIME: Extended evaluation period (30 days including today)
let $period_extended = 0d..60d;     // TIME: Maximum evaluation period (60 days including today)
```

### Purpose-First Exceptions

Safety and control variables use purpose-first naming for visual prominence:
```
let $safeguard_orders = 10;             // SAFEGUARD: Never pause keywords with 10+ lifetime orders
let $protected_terms = ["brand"];       // SAFEGUARD: Never negate search terms containing these keywords
let $bid_limit_cpc_multiplier = 2.0;   // SAFEGUARD: Max bid = Avg CPC × 2.0
let $excluded_campaigns = ["test"];    // FILTER: Exclude campaigns containing these terms
let $cooldown_period = 2d;             // TIME: Wait 2 days after last bid change
```

Purpose-first exceptions: `safeguard_*`, `protected_*`, `excluded_*`, `cooldown_*`, `*_limit_*`

### Array Variable Defaults
- Include arrays: `[""]` — matches all (empty string behavior)
- Exclude arrays: `["NEVER_MATCH"]` — excludes nothing
- Protected arrays: `["NEVER_MATCH"]` — protects nothing

---

## Comment Standards

### Required Comment Formats

**Target ACOS variables** — always include formula and example:
```
let $t_acos_threshold_increase = 80%;   // STRATEGY: Increase bids when ACOS <= (Target ACOS × 80%) [e.g., 30% target = 24% threshold]
```

**Buffer variables** — always include ± calculation and range:
```
let $t_acos_buffer = 10%;   // CORE: No-change buffer around target ACOS (Target ACOS ± 10%) [e.g., 30% target = 27-33% no-change zone]
```

**Multiplier variables** — always include calculation and concrete example:
```
let $cpc_multiplier = 2.0;   // ADVANCED: Max bid = Avg CPC × 2.0 [e.g., $0.50 CPC = $1.00 max]
```

**Array variables** — show usage examples and clarify behavior:
```
let $include_campaigns = [""];   // FILTER: Apply to all campaigns, or specify terms like ["SP-", "Auto", "Research"]
```

### Comment Tags

| Tag | Use for |
|---|---|
| `CORE` | Essential settings most users need to understand |
| `STRATEGY` | Segment-specific logic and behavior |
| `TIME` | Period definitions and timing controls |
| `ADVANCED` | Sophisticated features for power users |
| `FILTER` | Segment targeting and exclusions |
| `SAFEGUARD` | Protection and safety controls |

Align inline comments where possible. Add blank lines between setting groups.

---

## Section Organization

```
// === Core Settings ===       (always first)
// === Strategy Settings ===   (segment-specific logic)
// === Time Periods ===         (when relevant)
// === Advanced Settings ===   (power user controls)
// === Safeguards ===           (when needed)
// === Segment Filters ===      (always last)
```

Group safety variables prominently. Order from basic to advanced.

---

## Essential Code Patterns

Use these patterns in ALL segments.

### Multi-Period Data Selection

```
let $orders_recent = orders($period_recent);
let $orders_medium = orders($period_medium);
let $orders_long = orders($period_long);

let $evaluation_acos = case(
    $orders_recent >= $orders_min => acos($period_recent),
    $orders_medium >= $orders_min => acos($period_medium),
    $orders_long >= $orders_min => acos($period_long),
    else 99999  // Sentinel value for no reliable data
);
```

### Target ACOS Integration

```
let $acos_ratio = case(
    $evaluation_acos = 99999 => -1,         // No reliable data
    target acos <= 0 => -1,                 // Invalid target
    else $evaluation_acos / target acos     // Performance ratio
);

let $acos_acceptable_for_increase = case(
    target acos <= 0 => 0,                  // Invalid target
    $evaluation_acos = 99999 => 0,          // No data
    $evaluation_acos <= target acos * $t_acos_threshold_increase => 1,
    else 0
);
```

### Cooldown Check

```
let $cooldown_ready = case(
    is_null(last bid change) => 1,                                          // Never changed
    last bid change < now() - interval($cooldown_period) => 1,             // Grace period passed
    else 0                                                                  // Recently changed
);
```

### Safe Array Defaults

```
let $include_campaigns = [""];              // Matches all campaigns
let $exclude_campaigns = ["NEVER_MATCH"];  // Excludes nothing

and (campaign name contains any $include_campaigns)
and (campaign name does not contain all $exclude_campaigns)
```

> **CRITICAL:** Use `does not contain all` (not `any`) for exclusion filters. `does not contain any` uses OR logic — a campaign passes if it doesn't match ANY single item in the list, which means almost everything passes and the exclusion is silently useless. `does not contain all` uses AND logic — a campaign is excluded if it contains ANY item in the list, which is the correct behavior.

### State Filtering

```
state = "effectively enabled"
// Note: Search Terms dataset has no state property — skip this filter
```

### CPC-Based Dynamic Limits

```
let $avg_cpc = cpc($period_long);
let $dynamic_max_bid = case(
    $avg_cpc > 0 => $avg_cpc * $cpc_multiplier,
    else 999  // No limit if no CPC data
);

let $target_bid = case(
    $calculated_bid > $dynamic_max_bid => $dynamic_max_bid,
    else $calculated_bid
);
```

---

## Recommended Patterns

Use when adding sophistication.

### Adaptive Cooldown

```
let $adaptive_cooldown = case(
    orders($period_recent) >= $orders_min => $cooldown_period,
    orders($period_medium) >= $orders_min => $cooldown_period * 1.5,
    orders($period_long) >= $orders_min => $cooldown_period * 2,
    else $cooldown_period * 3
);

let $cooldown_ready = case(
    is_null(last bid change) => 1,
    last bid change < now() - interval($adaptive_cooldown) => 1,
    else 0
);
```

### Performance-Based Confidence Scaling

```
let $data_confidence = case(
    orders($period_recent) >= $orders_min => 1.0,
    orders($period_medium) >= $orders_min => 0.8,
    orders($period_long) >= $orders_min => 0.6,
    else 0.3
);

let $confidence_adjusted_change = $base_change_percent * $data_confidence;
```

---

## Advanced Patterns

Use sparingly, when justified by segment complexity.

### Multi-Factor Scoring

```
let $volume_score = case(
    clicks($period_recent) >= 50 => 1.0,
    clicks($period_recent) >= 20 => 0.8,
    clicks($period_recent) >= 10 => 0.6,
    else 0.3
);

let $recency_score = case(
    clicks(0d..3d) > 0 => 1.0,
    clicks(0d..7d) > 0 => 0.9,
    clicks($period_recent) > 0 => 0.7,
    else 0.4
);

let $composite_score = ($volume_score * 0.6) + ($recency_score * 0.4);
```

### Momentum Detection

```
let $recent_acos = case(orders(0d..7d) >= 1 => acos(0d..7d), else 99999);
let $previous_acos = case(orders(8d..14d) >= 1 => acos(8d..14d), else 99999);

let $momentum_signal = case(
    $recent_acos = 99999 or $previous_acos = 99999 => "insufficient_data",
    $recent_acos < $previous_acos * 0.8 => "improving",
    $recent_acos > $previous_acos * 1.2 => "declining",
    else "stable"
);
```

---

## Target ACOS Integration Guidelines

**Prefer Target ACOS adjustments over campaign filtering** when:
- Different campaign types need different thresholds (brand vs non-brand)
- Different match types require different aggressiveness
- Product categories have varying margins
- Account-wide strategy is changing

**Standard language for users:**
> "Adjust Target ACOS in Ad Manager for different campaign types rather than excluding campaigns. Target ACOS can be set at the account, campaign, ad group, or individual target level and will cascade down."

**Use campaign filtering instead** for: testing campaigns, paused campaign workflows, temporary exclusions.

---

## Property Priority

| Preferred | Over | Notes |
|---|---|---|
| `acos` | `roi`, `roas` | Primary efficiency metric |
| `orders` | `clicks` | More reliable for data checks |
| `target acos` | Hard-coded percentages | Always use account-level target |
| `state = "effectively enabled"` | `state = "enabled"` | Use where available |

**KDP segments use:**
- `blended acos` instead of `acos` (100% benchmark vs 30% standard)
- `blended profit` instead of `orders` for reliability checks (3 blended profit ≈ 1 order)
- `blended profit` instead of `sales` for revenue calculations

**KDP variable naming:**
```
let $blend_profit_min = 6.00;               // CORE: Minimum blended profit for reliable ACOS evaluation ($6.00 threshold)
let $t_blend_acos_threshold_increase = 80%; // STRATEGY: Increase bids when blended ACOS <= (Target Blended ACOS × 80%)
```

---

## Diagnostic Standards

Every segment must have **exactly two** diagnostic properties: `$reason` and `$planned_action`.

### Pattern 1: Nested Case (Simple Actions)
For single action type with meaningful magnitude ranges (bid management, budget adjustment):

```
let $planned_action = case(
    $action_needed = 1 => case(
        $change_percent >= $max_change => "Bid Increase: Maximum",
        $change_percent >= $max_change * 0.5 => "Bid Increase: Upper Range",
        $change_percent > 0 => "Bid Increase: Lower Range",
        $change_percent <= -1 * $max_change => "Bid Decrease: Maximum",
        $change_percent <= -1 * $max_change * 0.5 => "Bid Decrease: Upper Range",
        else "Bid Decrease: Lower Range"
    ),
    else "No Action"
);
```

### Pattern 2: Business Logic Focus (Complex Conditions)
For multiple blocking conditions or complex qualification logic:

```
let $reason = case(
    target acos <= 0 => "No target ACOS set",
    $evaluation_acos = 99999 => "Insufficient order data for reliable ACOS",
    $cooldown_ready = 0 => "Recently changed - in cooldown period",
    $acos_ratio <= $t_acos_threshold_increase => "ACOS below increase threshold",
    $protected_term = 1 => "Protected by safeguard rules",
    else "ACOS above target but within acceptable range"
);

let $planned_action = case(
    $action_needed = 1 => "Bid Adjustment Applied",
    else "No Action"
);
```

### Pattern 3: Performance Assessment (Analysis)
For segments that assess rather than act:

```
let $reason = case(
    $acos_trend = "improving" => "ACOS improving over evaluation period",
    $acos_trend = "declining" => "ACOS worsening over evaluation period",
    $impression_volatility = 1 => "High impression volatility detected",
    else "Stable ACOS performance maintained"
);

let $planned_action = case(
    $confidence_score >= 0.8 => "High Confidence Assessment",
    $confidence_score >= 0.5 => "Moderate Confidence Assessment",
    $data_sufficiency = 0 => "Insufficient Data",
    else "Low Confidence Assessment"
);
```

### Diagnostic Content Rules

**$reason — standalone performance assessment:**
- Explain WHY this state occurred — readable without other columns
- Good: "ACOS below increase threshold" | Bad: "Has sufficient data"
- Good: "Exceeds click-per-order limit" | Bad: "Below efficiency threshold"
- Reference user-controllable settings and seller terminology

**$planned_action — action with magnitude:**

*(Previously named `$result` in older segments — rename on any segment you touch. The data presentation standard and all templates use `$planned_action` as the canonical column name.)*
- Show WHAT with magnitude relative to user's configuration
- Good: "Bid Increase: Upper Range" | Bad: "Increase bid"
- For no-action cases: just "No Action", not "Continue Monitoring"

**Magnitude categories:**
- Maximum: at configured threshold limits
- Upper Range: 50–99% of max
- Lower Range: min to 50% of max

### Required Coverage for $reason

Before finalizing, trace ALL logic paths:
1. Invalid/missing target ACOS or required settings
2. Insufficient data (clicks, orders, spend)
3. Performance within acceptable range
4. Cooldown period active
5. Protected by safeguards
6. Performance above/below action thresholds
7. Edge cases specific to the segment

---

## Segment Structure Template

```
/*
=== [Segment Name] ===
Version: 1.0
Docs: merchjar.com/templates?t=[slug]

Purpose: [One sentence - max 20 words]
Dataset: [Dataset Type]
Recommended: [Action Type]: [Method] using [Variable] | [Schedule]
*/

// === Core Settings ===
let $orders_min = 2;                    // CORE: Minimum orders needed for reliable ACOS data

// === Strategy Settings ===
let $t_acos_threshold_increase = 80%;   // STRATEGY: Increase bids when ACOS <= (Target ACOS × 80%) [e.g., 30% target = 24% threshold]
let $bid_min_change = 3%;               // STRATEGY: Minimum bid change when adjustment is warranted
let $bid_max_change = 10%;              // STRATEGY: Maximum bid change regardless of performance gap

// === Time Periods ===
let $period_short = 0d..7d;             // TIME: Primary evaluation period (7 days including today)
let $period_medium = 0d..14d;           // TIME: Secondary evaluation period (14 days including today)
let $period_long = 0d..30d;             // TIME: Extended evaluation period (30 days including today)
let $cooldown_period = 2d;              // TIME: Wait 2 days after bid change before adjusting again

// === Advanced Settings ===
let $cpc_multiplier = 2.0;              // ADVANCED: Max bid = Avg CPC × 2.0 [e.g., $0.50 CPC = $1.00 max]

// === Segment Filters ===
let $include_campaigns = [""];              // FILTER: Apply to all campaigns, or specify terms like ["SP-", "Auto", "Research"]
let $exclude_campaigns = ["NEVER_MATCH"];  // FILTER: Exclude campaigns containing these terms, e.g., ["Brand", "Test", "Archive"]


// ============================================================================
// === Segment Logic ===
// ============================================================================
// Advanced logic below - modify carefully

// Multi-period data selection
let $orders_recent = orders($period_short);
let $orders_medium = orders($period_medium);
let $orders_long = orders($period_long);

let $evaluation_acos = case(
    $orders_recent >= $orders_min => acos($period_short),
    $orders_medium >= $orders_min => acos($period_medium),
    $orders_long >= $orders_min => acos($period_long),
    else 99999
);

// Target ACOS validation
let $acos_ratio = case(
    $evaluation_acos = 99999 => -1,
    target acos <= 0 => -1,
    else $evaluation_acos / target acos
);

let $qualifies_for_increase = case(
    target acos <= 0 => 0,
    $evaluation_acos = 99999 => 0,
    $evaluation_acos <= target acos * $t_acos_threshold_increase => 1,
    else 0
);

// Cooldown
let $cooldown_ready = case(
    is_null(last bid change) => 1,
    last bid change < now() - interval($cooldown_period) => 1,
    else 0
);

// Bid calculation
let $performance_gap = case(
    $acos_ratio <= 0 => 0,
    $acos_ratio < $t_acos_threshold_increase => ($t_acos_threshold_increase - $acos_ratio) / $t_acos_threshold_increase,
    else 0
);

let $bid_change_percent = case(
    $qualifies_for_increase = 1 => $bid_min_change + ($performance_gap * ($bid_max_change - $bid_min_change)),
    else 0
);

// CPC-based limits
let $avg_cpc = cpc($period_long);
let $calculated_bid = bid * (1 + $bid_change_percent);
let $dynamic_max_bid = case(
    $avg_cpc > 0 => $avg_cpc * $cpc_multiplier,
    else 999
);

let $target_bid = case(
    $calculated_bid > $dynamic_max_bid => $dynamic_max_bid,
    else $calculated_bid
);

// Action decision
let $action_needed = case(
    $qualifies_for_increase = 1 and $cooldown_ready = 1 and $target_bid > bid => 1,
    else 0
);

// Diagnostics
let $reason = case(
    target acos <= 0 => "No target ACOS set",
    $evaluation_acos = 99999 => "Insufficient order data for reliable ACOS",
    $qualifies_for_increase = 0 and $acos_ratio > 0 => "ACOS above increase threshold",
    $cooldown_ready = 0 => "Recently changed - cooling down",
    $target_bid = bid => "No bid change calculated",
    $calculated_bid > $dynamic_max_bid => "Limited by CPC-based maximum",
    $qualifies_for_increase = 1 => "ACOS below target threshold",
    else "Performance at target"
);

let $planned_action = case(
    $action_needed = 1 => case(
        $bid_change_percent >= $bid_max_change => "Bid Increase: Maximum",
        $bid_change_percent >= $bid_max_change * 0.5 => "Bid Increase: Upper Range",
        $bid_change_percent > 0 => "Bid Increase: Lower Range",
        else "No Action"
    ),
    else "No Action"
);

// === Final Filter ===
state = "effectively enabled"
and (campaign name contains any $include_campaigns)
and (campaign name does not contain all $exclude_campaigns)
and $action_needed = 1
```

---

## Quality Checklist

### Essential (all segments)
- [ ] Version number in header matching CMS field
- [ ] Target ACOS integration with validation
- [ ] Multi-period data selection with cascading case
- [ ] Data reliability checks (orders, clicks, or spend minimum)
- [ ] State filtering (where available)
- [ ] Safe array defaults (`[""]` and `["NEVER_MATCH"]`)
- [ ] Cooldown using `is_null()` pattern
- [ ] Exactly two diagnostics: `$reason` and `$planned_action`
- [ ] Conservative defaults (≤10% bid changes)

### Recommended
- [ ] CPC-based dynamic limits (not arbitrary caps)
- [ ] Aligned comments with tags
- [ ] Blank lines between setting groups
- [ ] Edge cases handled (missing target ACOS, no data, exactly at thresholds)

### Review Focus
- Variable naming follows patterns or has documented justification
- Comments include required formatting (formulas for Target ACOS, examples for multipliers)
- Diagnostic $reason covers all major logic paths
- Final filter includes all necessary conditions
- Segment serves its stated purpose effectively

---

## Standards Flexibility

Override standards when segment-specific context makes a different approach better for users. Always maintain:
- Target ACOS integration over hard-coded thresholds
- Safe array defaults and state filtering
- Two diagnostic properties
- Essential code patterns for data reliability
- Version number in header

Document deviations with comments explaining the segment-specific reasoning.
