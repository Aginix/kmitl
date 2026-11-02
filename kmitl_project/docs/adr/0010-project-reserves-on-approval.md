# A project reserves its budget when it is approved, not before

> **Amends** [ADR-0005](./0005-approval-gated-lifecycle-esaraban.md) and [ADR-0006](./0006-project-allocation-before-reserve.md): the `to_verify → to_send` step no longer reserves.

A project used to reserve its `budget.commitment` at `to_verify → to_send` ("จองงบประมาณ"), *before* its ขออนุมัติ หนังสือ was sent. That commitment could not be spent until the project reached `in_progress` — the พ.1 and approval-request pickers already gate on `kmitl_project_id.state = in_progress` — so the money sat locked for nothing, had to be cancelled and re-reserved on every ตีกลับ (`_resync_project_commitment`), and released again on ปฏิเสธ. The project dimension already earmarks the money: งานแผน's **Project Allocation** keeps it at the project's own coordinate, so nobody else can take it in the meantime.

The flow is now `draft → to_verify (งานแผนจัดสรร) → to_send → sent → [ลงนามครบ = จองงบอัตโนมัติ] → in_progress`.

## Decisions

- **`to_verify → to_send` becomes "ยืนยันงบประมาณ".** Same method (`action_reserve_budget`, kept for the views that xpath it) and the same wizard, which still requires `budget_amount > 0` and every plan line positive, and still pins the budget code + dimensions (the หนังสือ quotes them) — but it no longer creates a commitment.
- **Approval reserves.** `_approve_project()` (called by the manual `action_approve` and by the bridge's `_on_sarabun_completed`) reserves the full `budget_amount` via `_reserve_project_commitment()` and moves the project to `in_progress`. Under the หนังสือ callback it runs on `origin.sudo()` (agx_sarabun `_call_origin`), so the last signer needs no budget rights; the commitment's `user_id` is the project's creator, not the signer.
- **A failed reservation never blocks the approval.** The reserve runs in a savepoint; a `UserError` (incl. `ValidationError` / `AccessError`) is rolled back and posted to the chatter ("อนุมัติโครงการแล้ว แต่ยังจองงบประมาณไม่ได้: …"), and the project still lands in `in_progress`. This deliberately departs from agx_sarabun [ADR-0004](../../../agx_sarabun/docs/adr/0004-integration-adapter-contract.md)'s "no silent swallow": the signature is the authority's decision and must not be undone by a budget figure that moved after the หนังสือ was sent; the failure is not silent — it is recorded on the project, and without a commitment the project still cannot raise a พ.1 or an approval request (the pickers find no slip). A "จองงบประมาณ" button (`action_retry_reserve_budget`) appears on an `in_progress` project with nothing reserved and retries, surfacing the error this time. In practice the reserve passes, because the amount reserved *is* the money allocated at the project's coordinate.
- **No migration.** `_reserve_project_commitment` is idempotent, so legacy projects already reserved at `to_send`/`sent`/`returned` keep their single commitment through approval; `_release_project_commitment` / `_resync_project_commitment` are untouched and simply have nothing to do for projects that have not reserved yet.

## Consequences

- Top-ups while awaiting approval need nothing: they raise `budget_amount` and the approval reserves the full figure. Top-ups after reservation still go through `kmitl_project_budget_transfer` (budget ADR-0017).
- Rejecting, cancelling or resetting a not-yet-approved project releases nothing, because nothing was reserved. Cancelling an approved project keeps its commitment (`in_use`), as before.
- The dashboard still counts `budget_amount` from `to_send` on — the allocated figure, not the reservation.
- The 500,000 dean/president threshold still reads `budget_amount` when the หนังสือ is created.
