# Exception rules are split into advance_payment_exception

Status: accepted (2026-10 UAT feedback; pre-production, no migration/version bump)

## Context & Decision

The core inherited `base.exception` and shipped the submit-time rules, the popup wizard and the Exception Rules menu. That tied the loan lifecycle to `base_exception` even for code (tests, programmatic creation) that never wanted rule evaluation.

**All** of it moves to `advance_payment_exception`: the `base.exception` inheritance (`_order`, `_reverse_field`, `_get_popup_action`, the to_endorse/to_verify constraint), the submit-time popup, the popup wizard, the rule menu, the form banner and list column, and every rule, **including the mandatory ones** (missing bank account, missing reference, missing manager, amount limits).

- The module is `auto_install=True`, so any database with `advance_payment` gets it. The mandatory rules are therefore always present in practice.
- `action_submit` is overridden there: a draft with exceptions and no `ignore_exception` returns the popup; otherwise it calls super.
- `excep_missing_bank_account` becomes `by_py_code` so it understands the unlisted bank account (ADR-0022).
- The bridges whose `exception.rule` data needs the model (`agx_approval_advance_payment`'s headroom rule, `advance_payment_budget`'s dimensions rule) add `advance_payment_exception` to `depends`.

## Why

- One module owns the exception mechanism. The core's tests and lifecycle no longer depend on rule data.
- Keeping the mandatory rules together with the optional ones avoids a split where half the rules live in the core and need `base_exception` anyway.
- `auto_install` keeps the rules from being forgotten on a fresh database.

## Consequences

- Without `advance_payment_exception`, submit performs no rule checks. Only the hard guards stay in the core: the one-active rule, the reference/type match, and verify needing `bank_id`.
- A new auto-install module is not picked up by `-u`. Existing databases must `-i advance_payment_exception`.
