# The DR's two axes live in core, not in `disbursement_wc`

The ใบขอเบิก has two independent axes. **`state`** is progress around the วงจร
(draft → submitted → signed → in progress → done, or cancel). **`settlement_stage`**
(ขั้นการชำระ: none → billed → settled → booked) says how far the money has got, and is a
stored compute derived from the bills and vouchers that exist, so it walks back by itself.
Both fields, and the `can_edit_*` locks that read them, are declared in **`disbursement`**.
`disbursement_accounting_kmitl` and `disbursement_finance_kmitl` contribute their legs of
the stage; `disbursement_wc` contributes only the station half of each lock.

This amends the module split of the station design, which placed the state collapse, the
stage and the locks in `disbursement_wc`.

## Why

- **Readers must not need the engine.** `kmitl_project_disbursement`,
  `procurement_plan_disbursement`, `agx_approval_disbursement`,
  `purchase_request_approval_disbursement` and `advance_payment_disbursement` read the
  request's state and the money's progress. Declared only in `disbursement_wc`, those
  fields would be missing — and the registry would fail to load — wherever the engine is
  not installed.
- **Core stays independent of `work_center`.** The seams (`_on_signed`, the act checks,
  `_can_edit_open` / `_can_edit_blocked`, `_on_settlement_walked_back`) are named for the
  capability, never for the station, so an installation with no stations still works: a
  signed request simply stays signed.

## Considered options

- **Everything in `disbursement_wc`.** Rejected: every reader would depend on the engine,
  which would pull `work_center` into every budget consumer.

## Consequences

- With no `disbursement_wc` (or no active route) a request goes draft → submitted → signed
  and stays there; every act is offered at `signed` to its role.
- The three approval acts leave core for their own modules. Their stamp columns move with
  them, so an upgrade must install the act modules in the same command as `-u disbursement`,
  or Odoo drops the columns.
