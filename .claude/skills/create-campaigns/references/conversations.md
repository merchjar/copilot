# Illustrative conversations

These are examples, not recorded acceptance evidence. Account context is assumed resolved unless stated otherwise.

**Guided first launch**

User: I've attached ten ASINs. Help me choose a launch setup.

Copilot: Do you want a separate budget for each product, or are some of these products meant to be advertised together?

User: Separate budgets. I don't have keywords yet.

Copilot: We can build Auto, Research and Exact for each product, with dummy keywords in the manual campaigns. I'll stage them paused. What daily budget would you like per campaign? There will be 30 campaigns.

The next response uses the supplied amount, resolves bids, shows overlap and eligibility gaps, and presents all thirty campaigns, groups and Product Ads plus ten BROAD and ten EXACT dummy keywords before asking for creation approval. Copilot supplies the terms; the user uploads ASINs only. Empty manual groups are not needed for this path.

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

**Partial result**

Copilot reports confirmed successes separately from a Product Ad eligibility error and a campaign whose result is unknown. It creates no children for the unknown campaign and makes no blind retry. The report describes exactly what still needs verification.
