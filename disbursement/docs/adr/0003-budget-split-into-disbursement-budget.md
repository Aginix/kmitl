# Budget control lives in `disbursement_budget`, not in the core request

`disbursement` used to depend on `budget`: the request inherited
`budget.commitment.mixin`, carried the commitment / budget-code fields, consumed
the commitment on the Rector-delegated approval and reversed it on cancel. A
stand-alone ใบขอเบิก — one raised without any budget control, e.g. by a unit that
does not run the budget module — could not exist.

## Decision

Everything budget-related moves to a new **`disbursement_budget`** (depends
`disbursement` + `budget`, `auto_install`), and `disbursement` no longer depends
on `budget` at all. Core keeps two empty workflow hooks the bridge fills in:

- `_on_final_approval()` — called by `action_approve` (the Rector step, ADR 0001)
  before the request turns `approved`; `disbursement_budget` consumes the linked
  commitment here, and raising aborts the approval.
- `_on_cancel()` — called per request by `action_cancel`;
  `disbursement_budget` reverses this request's events, or cancels the whole
  commitment when no other request shares it.

The four financial dimensions (แหล่งเงิน / ส่วนงาน / กองทุน / กิจกรรม) **stay in core**:
they come from `account_analytic_kmitl`, not `budget`, and a stand-alone request
still records where the money is charged.

## Considered options

- **Split the code but keep `budget` in core's depends (rejected)** — a smaller
  move, but it does not deliver the stand-alone request the split exists for.
- **Move the dimensions too (rejected)** — would leave a stand-alone request with
  no analytic charge, and every finance list groups by แหล่งเงิน.

## Consequences

- Bridges that write or read the budget fields depend on `disbursement_budget`
  instead of `disbursement`: `agx_approval_disbursement`,
  `kmitl_project_disbursement`, `procurement_plan_disbursement`,
  `purchase_order_disbursement_budget`,
  `purchase_request_approval_disbursement_budget`,
  `disbursement_accounting_kmitl`, `finance_kmitl_demo`. The Sarabun body's
  budget rows move to the auto-install glue `disbursement_sarabun_budget`.
- The bridge's form inherit runs at priority 10 so it applies before bridges'
  inherits that already exist on upgraded databases (lower ids) and reference
  the budget fields it adds.
- **Upgrade (production):** the `16.0.11.0.0` pre-migration re-points the moved
  fields' and view's external ids to `disbursement_budget` — otherwise upgrading
  `disbursement` would unlink them and drop the columns — and queues
  `disbursement_budget` / `disbursement_sarabun_budget` for install, since `-u`
  never installs a new auto-install module on its own. Deploying with an explicit
  `-i disbursement_budget,disbursement_sarabun_budget` is still the safe call.
- Core tests stub `_on_final_approval` on the registry class so they pass with or
  without the bridge; the budget assertions moved to `disbursement_budget/tests`.
