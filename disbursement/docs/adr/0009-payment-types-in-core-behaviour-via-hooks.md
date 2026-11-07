# Payment types are declared in core; their behaviour comes from add-ons through hooks

Core `disbursement` declares all three payment types: จ่ายตรง (`direct`), เงินยืม
(`advance`) and สำรองจ่าย (`prepaid`). Core has no branch for any one type. What
differs between them comes in through two compute hooks that core sets to True:

- `pays_out`: whether the request pays money out. When it does not, the request has no
  bank account and no payment method.
- `can_have_tax`: whether the request may be taxable. When it may not, มีภาษี is hidden
  and forced off.

`advance_payment_disbursement` overrides both for `advance`. It also names the loan the
request clears and clears that loan at ตัดงบ.

The only core rule that reads the type is written against `direct`: only จ่ายตรง may pay
a non-internal payee type.

## Why

- **The stored value must survive without the add-on.** Prod already holds advance
  requests while `advance_payment` is not installed there. If the value came from a
  `selection_add`, those rows would need a data migration, and every other module that
  lists the type would disagree with core about which types exist (for example
  `disbursement_payment_subject_rule`).
- **Core stays loan-agnostic.** Hooks let an add-on change behaviour without core
  naming it.

## Considered options

- **Add `advance` with `selection_add` in the bridge.** Rejected for the reasons above.
- **Keep the advance logic in core.** Rejected: core cannot name or clear a loan, so the
  logic would be half a feature.

## Consequences

- Without `advance_payment_disbursement`, เงินยืม is still offered, and it behaves like
  any internal-staff request: it pays out and may be taxable.
