# Project deletion replaces cancel; held money must be returned to its source first

> **Supersedes** the Cancel path of [ADR-0005](./0005-approval-gated-lifecycle-esaraban.md) and decisions #4 (retargeting strands the allocation) and #6 (cancel/reject leave the allocation for งานแผน to reverse) of [ADR-0006](./0006-project-allocation-before-reserve.md). **Extends** [ADR-0009](./0009-direct-floating-allocation-skips-transfer-approval.md) with the reverse move.

A project's own analytic account and the money on it had no clean end of life. Cancelling left the analytic selectable and the money stranded at the project's dimension. Deleting a cancelled project left the analytic orphaned, and deleting the analytic would have left dead ids in the ledger's `analytic_distribution`. Changing the รหัสงบ/มิติ after allocation stranded the money on purpose. Money could come in from the floating pool, but there was no way to send it back.

## Decisions

1. **One action, ลบโครงการ, three outcomes.** A project whose analytic has no **Ledger Footprint** (no other document has ever carried it, in any state) is deleted together with its analytic. A project with a footprint that has never spent is **soft-deleted**: `state = cancel` and both the project and its analytic are archived. Reset to draft brings both back and keeps the Project Number. A project that has spent cannot be deleted; it is closed (ปิดโครงการ) instead. The `cancel` state stays (existing rows, dashboard, portal, e-Saraban bridge) but has no button of its own.
2. **Deletion never moves money.** It is blocked while the project has **Held Money** (a non-zero net allocation on any coordinate in any fiscal year, an active reservation, or a transfer still in progress), an open purchase request/approval request/disbursement, or a circulating หนังสือ. The message names the amount and points to โอนคืนงบลอย.
3. **Floating Return (โอนคืนงบลอย) goes back by the project's own coordinate.** Whatever transfer brought the money in, it goes back as Floating Budget to the pool covering the project's รหัสงบ + four dimensions — the very pool a Direct Floating Allocation draws from, at that coordinate or the coarser one above it — so it never opens a pool nested with it (budget ADR-0016); with no pool left there, to the project's own coordinate. The user only picks the amount, up to the allocation minus the largest claim on it — what is obligated or consumed, or the total the project's พ.1, ใบขออนุมัติ or ใบขอเบิก are capped by (a พ.1 drawing the reservation posts nothing to the ledger, yet the money is spoken for). Moving money out of a reserved coordinate releases the unobligated reservation in the same move (budget ADR-0017).
4. **The same access as the allocation.** Any Budget User can return money. There is no หนังสือ; the transfer posts at once and is flagged for audit. It is allowed whenever the project has an analytic, except in `to_send`/`sent`, where the amount is pinned for the ขออนุมัติ หนังสือ.
5. **No retargeting while money is held.** The รหัสงบ and the four base dimensions can only change in draft/to_verify/returned **and** when the project holds no money. To change them: return the money, change the target, allocate again. The one exception is moving the target onto the coordinate where the money already sits, which strands nothing: projects retargeted before this rule hold money at an old coordinate, which only the project's own coordinate can return from, so they move back first.
6. **Closing returns the unspent reservation.** ปิดโครงการ is blocked by open downstream documents, then returns the leftover reservation (คืนจอง) automatically. The money stays free at the project's dimension until a Budget User returns it (filter "ปิดแล้วมีเงินค้าง").
7. **Who can delete.** A draft with no Project Number can be deleted by any Project Owner (หัวหน้าโครงการ, ผู้ประสานงาน or the creator). A numbered project can only be deleted by project officers, because the gap it leaves in the running numbers has to be accountable.
8. **One transfer bridge.** `kmitl_project_floating_allocation` is merged into the auto-installed `kmitl_project_budget_transfer`, which now holds both directions. That way the return the delete and retarget rules point to is available wherever budget transfers are installed.

## Considered options

- **Keep Cancel and allow delete only for projects with no footprint.** Rejected: once deletion is guarded this strongly, a separate cancel adds nothing and leaves two ways to retire a project.
- **Let the delete button return the money itself.** Rejected: the person deleting (often a coordinator) may have no budget rights, and moving money should be a deliberate step with its own BTR.
- **Return to where the money came from (each inbound transfer's FROM coordinate).** Rejected: the money belongs to the project's own รหัสงบ/มิติ once it is allocated, and งานแผน manages it from there; a supporting unit's money is moved on with an ordinary Budget Transfer if it has to go back to that unit.
- **Delete the analytic even when it has history.** Rejected: the ledger keeps the id in its JSON distribution, so the history would break.

## Consequences

- `procurement_plan` had the same gap (its delete only checked `account.analytic.line`). It now uses the same footprint check.
- Existing cancelled projects that hold no money are archived (with their analytic) by migration. Those that still hold money stay visible so the money can be returned.
- Carry-over (เงินกันเหลื่อมปี) and changing `project_type` are out of scope.
