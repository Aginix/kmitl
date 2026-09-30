# Requester selects the budget; only a budget officer reserves it

Selecting a budget code/dimensions (`budget_account_id` + the four analytic dimensions) and reserving budget (minting the `budget.commitment` that locks availability) were fused onto one gate — the entire budget block was hidden behind `budget.group_budget_commitment`, with the fields themselves `readonly="1"` and fillable only through the balance-showing reservation picker. A plain requester could therefore select nothing, which is a live conflict with `purchase_request_budget`'s exception rule requiring these fields at `to_verify`.

This splits the two capabilities. **Select** moves into a new, ungated "เลือกงบประมาณ" group as plain editable `Many2one` dropdowns — no balance exposure, no chart picker — open to any requester while `is_budget_editable` (unchanged compute; already correct per state/group). **Reserve** — the button, the mode radio, the reservation (draw-down) picker, and the balance-showing chart picker — stays exactly as before, gated to `budget.group_budget_commitment`, with a matching server-side guard added to `action_reserve_budget` (defense-in-depth against RPC and the draw-down path).

A category's pinned `budget_account_id` ([ADR-0004](0004-budget-code-selection-scoped-by-category-non-procurement.md)) still constrains selection: the requester-facing dropdown is bound to a new computed `budget_account_domain`, which returns `_reservation_account_domain()` — the same domain the reservation picker already enforces — instead of the field's own static domain, which cannot see `category_id`.

## Considered Options

- **A new group for "select budget"** (e.g. a `group_budget_select`) — rejected: no new capability actually needs a new group. The requester already owns the record (they can edit every other field on their own draft/to_verify request); nothing about writing `budget_account_id`/dimensions touches `budget.commitment` or needs new ACLs (`base.group_user` already reads `budget.account` and `account.analytic.account`).
- **A balance-showing picker for requesters too** — rejected: exposes organisation-wide budget balances (ยอดคงเหลือ) to every requester, which is a bigger disclosure than "let them type a code". Plain dropdowns match the existing precedent (`disbursement.request`, `disbursement/views/disbursement_request_views.xml`), which already renders all five fields as ungated editable dropdowns.
- **Mandate selection on `agx_approval` too** (a pre-`to_verify` exception requiring the fields) — deferred, not rejected: base keeps guards as-is (enable, not mandate); `purchase_request_budget`'s existing exception rule is unchanged and is now satisfiable. Adding a matching rule to `agx_approval` is a follow-up if requesters are found skipping selection in practice.

## Consequences

- `budget.group_budget_commitment` no longer means "can see the budget block" — it means "can reserve/draw". Selecting is open to anyone who can edit the request. See the CONTEXT.md glossary entry "Select vs Reserve".
- The requester-visible SELECT group is hidden once a live commitment exists (`budget_commitment_id` set and not cancelled) — the read-only commitment card above it is the only budget UI shown from that point on, for everyone.
- `purchase_request_budget` mirrors this split with the same shape: a new ungated "เลือกงบประมาณ" group carrying the existing `to_verify_budget` `required` attrs, and a computed `budget_account_domain` that folds in the `budgetable`/`expense` baseline its own static domain omits.
- Supersedes the old convention of gating the whole budget selection UI on `budget.group_budget_commitment`; any future budget-consumer host view should follow this split, not the old single-gate pattern.
