# Context Map

This is a multi-module Odoo monorepo. Each custom module is its own bounded context, documented by a `CONTEXT.md` (glossary) and an optional `docs/adr/` (architecture decisions) inside the module folder.

This map is seeded lazily — modules are listed here as they get a `CONTEXT.md`, not upfront.

## Contexts

- [KRIS Project](./kris_project/CONTEXT.md) — revenue tracking for projects run under the KRIS unit (operating unit `99`); external academic-service and research work channelled through KRIS.
- [KRIS Project — In Cash / In Kind](./kris_project_in_cash_in_kind/CONTEXT.md) — optional split of a research project's `project_value` into `in_cash` (cash KRIS receives) and `in_kind` (matching funds that never touch KRIS's cash accounts); anchors every cash-flow compute on `in_cash` when installed.
- [Budget](./budget/CONTEXT.md) — appropriation, reservation and disbursement tracking; appropriated pool (`budget.move`) consumed through a reserve→obligate→consume commitment pipeline (`budget.commitment`).
- [Budget Revenue Comparison](./budget_revenue_comparison/CONTEXT.md) — configurable report setting **budgeted revenue** (`budget.move`, revenue codes) beside **actual revenue** (`account.move.line`, income types) row by row; each row carries two independent selectors because the budget chart and the CoA have no stored link.
- [Procurement Plan](./procurement_plan/CONTEXT.md) — annual procurement planning; each plan is created from an appropriation, reserves its budget at that moment, and is realised through one purchase request + installment disbursements.
- [KMITL Project](./kmitl_project/CONTEXT.md) — institutional project/activity planning (โครงการ/กิจกรรม); a project draws from a *floating* project-type budget pool, reserves its full budget when confirmed, then spends like a procurement plan.
- [Accounting Reports](./accounting_kmitl_reports/CONTEXT.md) — financial-statement reports (Trial Balance, P&L, Balance Sheet, Cash Flow) over the GL (`account.move.line`), filterable by the KMITL accounting dimensions.
- [Accounting Workflow](./accounting_kmitl_workflow/CONTEXT.md) — two-step maker-checker approval every `account.move` passes before posting (Submit by ผู้จัดทำ/ผู้ตรวจสอบ → Approve by ผู้อนุมัติ = post); a custom `workflow_state` + computed `display_state` overlaid on the existing `draft→submitted→posted` flow, plus a journal-items voucher report with a signature block.
- [Identity & Access](./iam/CONTEXT.md) — standalone app that delegates backend user/role/group/OU/access-right/record-rule administration without granting full Settings (`base.group_system`); a single `IAM Manager` group implying `erp_manager` plus one escalation guard.
- [Todos](./mail_activity_todo/CONTEXT.md) — cross-cutting unified inbox (สิ่งที่ต้องทำ) of everything a user must act on; each Todo is a native `mail.activity` on its source record, surfaced in one consolidated page with a jump-to-source button. Owns no business state.
- [e-Saraban](./agx_sarabun/CONTEXT.md) — electronic official-correspondence (งานสารบรรณ); a registered, numbered หนังสือ routed through an approval/endorsement chain. Other modules attach as origin records that spawn a Document.
- [Approval ↔ Disbursement Bridge](./agx_approval_disbursement/CONTEXT.md) — links an Approval Request to the Disbursement Request it is billed into; returning a disbursement keeps it intact (at `signed`) and bounces the approval request to `returned`, where the requester corrects a limited set of fields and confirms to push them back onto the disbursement.

## Relationships

- **Budget → Procurement Plan**: posting a `budget.appropriation` line creates a `procurement.plan` and reserves its `budget.commitment` for the full amount (ADR-0005).
- **Procurement Plan → Budget**: the plan's single purchase request and its installment disbursement requests draw that one shared commitment down (obligate+consume per งวด) (ADR-0004, ADR-0006).
- **Budget → KMITL Project**: posting an appropriation on an `is_project` budget code leaves the pool *floating* — it does **not** auto-create a project or reserve (contrast Procurement Plan). A `kmitl.project` reserves its `budget.commitment` for the full `budget_amount` when confirmed (`draft→new`) (ADR-0007).
- **KMITL Project → Budget**: the project's purchase requests (พ.1) and disbursements draw that one shared commitment down (obligate+consume); a project may hold many PRs, capped at the commitment (ADR-0007).
- **Disbursement / Finance → Accounting Workflow**: disbursement vendor bills and payments no longer post directly — their `account.move` enters the approval and is posted by Approve. Payment moves additionally keep the finance bank-export gate (Submit → Bank Export → Approve=post).
- **Disbursement → Approval (return)**: returning a `disbursement.request` at `signed` keeps it untouched (still `signed`, budget unchanged) and bounces the linked `approval.request` to `returned`; the requester corrects only the payee bank, description and disbursement evidence, then **Confirm Correction** pushes those onto the kept disbursement and moves the AR back to `billed` (`agx_approval_disbursement` ADR-0001).
- **All contexts → Todos**: a workflow schedules/clears a `mail.activity` (a Todo) at its own state transitions; Todos only aggregates and surfaces them and holds no business state (`mail_activity_todo` ADR-0001). v1 source is Procurement Plan only; the next actor is either a single user or a role-in-unit group (`base_user_role` role ∩ operating unit, resolved live — `mail_activity_todo` ADR-0002); dynamic `tier.validation` routing is deferred.
- **KRIS Project → In Cash / In Kind**: `kris_project_in_cash_in_kind` inherits `kris.project` and, on research projects, turns `project_value` into a derived sum of `in_cash + in_kind`; every cash-flow compute repoints from `project_value` to a `cash_target` that equals `in_cash` on research and `project_value` elsewhere. Base module behaviour is unchanged when the add-on is not installed.
