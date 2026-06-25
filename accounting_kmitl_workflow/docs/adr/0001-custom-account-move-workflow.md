# Custom maker-checker workflow on account.move (not tier.validation)

The account.move approval is built as a **custom `workflow_state` field + computed `display_state`** rather than the OCA `tier.validation` mixin, even though `base_tier_validation` is already a dependency, `account_move_tier_validation` exists in the addons path, and the repo uses `tier.validation` elsewhere (advance_payment, work_acceptance). We chose custom because `accounting_kmitl` already invests in a `draft → submitted → posted` state machine (`action_submit`, `_compute_hide_post_button`), and we want **Submit → Approve → auto-post** with the maker's submit as step 1. `account_move_tier_validation` keys off `draft → posted` (no `submitted` step) and overrides `_compute_hide_post_button` against `need_validation`, which would fight the existing submitted flow; reconciling the two would be more code and more surprise than a purpose-built field that extends the flow we already have.

## Consequences

- The "who did what" audit that `tier.validation.review_ids` gives for free is built by hand as `submitted_by`/`submitted_date`/`approved_by`/`approved_date`, which also feed the voucher report's signature block.
- The gate is enforced at the UI layer only (the manual Post button is always hidden; Approve posts). Nothing blocks `_post()`/`action_post()`, so system-generated moves never deadlock.
- `finance_kmitl` previously shipped a dormant `tier.definition` for payment moves on `account.move`; it was removed to avoid a latent trap if `account_move_tier_validation` were ever installed.
