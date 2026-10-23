# Illustrative conversations

These are examples, not recorded acceptance evidence. Account context is assumed resolved unless stated otherwise.

**Guided first launch**

User: I've attached ten ASINs. Help me choose a launch setup.

Copilot: Do you want a separate budget for each product, or are some of these products meant to be advertised together?

User: Separate budgets. I don't have keywords yet.

Copilot: We can build Auto, Research and Exact for each product, with dummy keywords in the manual campaigns. Research and Exact also get a product-targeting ad group. These products have no search terms yet, so those groups start empty and won't serve until you add ASINs. I'll stage everything paused. What daily budget would you like per campaign? There will be 30 campaigns.

The next response uses the supplied amount, resolves bids, shows overlap and eligibility gaps, and presents all thirty campaigns, fifty groups and Product Ads plus ten BROAD and ten EXACT dummy keywords before asking for creation approval. Copilot supplies the terms; the user uploads ASINs only. The twenty product-target groups are listed as empty, with no invented ASINs.

**Returning user**

User: Create campaigns for these ASINs.

Copilot: I'll use your saved Launch setup for this account: Auto, broad Research and Exact for each product. What daily budget would you like per campaign?

Ask about keywords only if their readiness remains unknown. Do not repeat the structure question. If the user already supplied the budget, use it and recompute the total for this batch.

**One-time change**

User: Use Launch, but skip Exact this time. Keep the total at 90 euros.

Copilot updates this plan, explains how the allocation changes across the remaining roles, and leaves Launch unchanged. Approval of an earlier three-role plan does not authorize the changed batch.

**Save after an explicit instruction**

User: Remember this as my default launch setup for this account.

After successful storage, Copilot: Saved Launch as this account's default launch setup. I'll still ask for the new batch's budget.

**Multiple saved choices**

User: Create discovery campaigns for these products.

Copilot: You have two saved discovery setups: Auto discovery, with one Auto campaign per product, and Seed testing, with broad campaigns for supplied terms. Which fits this batch?

**Ambiguous budget**

User: Five euros daily.

Copilot: Do you mean EUR 5 per campaign, or EUR 5 across the whole batch? EUR 5 per campaign would be EUR 150 total for these 30 campaigns.

An explicitly selected EUR 5 batch total cannot be spread below the campaign minimum. Explain the valid alternatives without changing the amount or structure automatically.

**Enabled manual parents, paused dummy keywords**

User: Enable the campaigns, but leave the dummy keywords paused.

Copilot includes enabled campaign, group and Product Ad states and paused dummy keywords in the plan. It explains which Auto or real targets will serve, creates and reconciles the paused structure, then applies only the approved enablement. It never claims placeholders make parent enablement impossible.

**Product targets from search terms**

User: Add Research and Exact for B0EXAMPLE1. It's been selling in my Auto campaign.

Copilot reads that product's search terms that sold over the last 60 days. Three ASINs sold in ad groups that advertise only this product, so it proposes them as exact targets in the Exact product-target group and as expanded targets in the Research one, with their order counts and cost per click. Two more sold in a group shared with other products; it lists them separately and asks whether to include them, because the report can't say which product made those sales.

**User-supplied ASINs**

User: Target these two competitor ASINs in Exact.

Copilot adds them as paused exact targets in the Exact product-target group. It asks whether Research should get expanded targets on the same ASINs rather than assuming it.

**Skip product targeting**

User: No product targeting this time.

Copilot drops both product-target groups from this plan only. If the user says to remember it, it saves `product_group: skip` on the Research and Exact roles of the saved structure.

**Partial result**

Copilot reports confirmed successes separately from a Product Ad eligibility error and a campaign whose result is unknown. It creates no children for the unknown campaign and makes no blind retry. The report describes exactly what still needs verification.
