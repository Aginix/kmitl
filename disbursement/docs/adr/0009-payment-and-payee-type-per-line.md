# Payment type and payee type live on the line

Reverses "one request per payee type" (CONTEXT.md). `payment_type` (ประเภทการจ่ายเงิน)
and `partner_type_id` (ประเภทผู้รับเงิน) move from `disbursement.request` to
`disbursement.request.line`, so one ใบขอเบิก may mix payees and ways of paying — a PO
paying a company and a staff member, or a request clearing two loans next to a direct
payment. The line list gains free **sections** and notes (`display_type`, as on
`sale.order`).

## Decision

- **Selection + hooks.** `payment_type` stays a Selection with unchanged keys; core
  ships `direct` and `prepaid`, and `advance_payment_disbursement` adds `advance` by
  `selection_add` (its `ondelete` refuses to drop loan lines silently). Behaviour sits
  behind line hooks add-ons override: `_pays_out()`, `_requires_internal_payee()`,
  `_default_taxable()`, `_bill_group_key()`.
- **Payee type follows the payee.** A stored compute from `partner_id` (a snapshot),
  editable, narrowing the payee picker; a mismatch is a submit exception.
- **Header keeps summaries only.** `payment_type_display` / `payee_type_display` are
  non-stored Chars for the list and the print; `has_tax` stays a manual header switch.
- **Bills split by `_bill_group_key()`** — partner and payment type in core, plus the
  loan with `advance_payment_disbursement`. Each bill line remembers its request line
  (`account.move.line.disbursement_request_line_id`).
- **Loan per line.** Each เงินยืม line names its loan; ส่งใช้คืน is the sum of that loan's
  lines on consumed requests, so one request may clear several loans.
- **หัวจ่าย per payment line.** `disbursement.payment.line.payment_subject_id`; the
  request's subject becomes "set all", and the subject rules match each payment line
  on the types of its bill's request lines.

## Considered options

- **Header as default, lines may override** — rejected: two places to read the same
  fact, and every reader must know which wins.
- **A configuration model (M2o) for payment types** — rejected: the behaviour differs
  per type in code anyway; a Selection with hooks keeps it in the module that owns it.
- **Forbid mixing payment types in one request** — rejected: sources (PO, PA, AR) pay
  mixed payees and would still be split into many requests.

## Consequences

- One `-u` of every touched module (prod has `advance_payment_disbursement`); the core
  pre-migration copies the header values onto the lines.
- Every reader of `line_ids` skips `display_type` rows.
- PR/PA keep their own header `payment_type`; a PA → DR does not map it.
