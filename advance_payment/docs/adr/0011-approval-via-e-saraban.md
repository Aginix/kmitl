# Approval at `to_approve` routes through e-Saraban when `advance_payment_sarabun` is installed

Status: accepted (2026-08; UAT-only) — amends ADR-0006

## Context & Decision

A new bridge module, `advance_payment_sarabun`, lets `to_approve` circulate an official e-Saraban หนังสือ instead of (or in addition to, as a manual fallback) the direct อนุมัติ button. It reuses `to_approve` as the circulating state — **no new state is added** to `advance.payment`. The loan officer (`group_advance_payment_loan_officer`) raises the หนังสือ ("สร้างหนังสือ") from `to_approve`; the base manual "อนุมัติ" button is hidden once the bridge is installed, so approval flows exclusively through Sarabun.

Route: single-step, targeting a holderless `sarabun.position` (real holder assigned in Configuration before go-live) — the org-routed multi-tier chain from ADR-0006 stays deferred, but is now realizable later purely through Sarabun route configuration, without touching this module again.

Outcome mapping, driven by the mixin's lifecycle callbacks:

| Sarabun outcome | Loan transition |
|---|---|
| Completed (ลงนามครบ) | calls base `action_approve()` — creates the disbursement `account.payment`, moves to `waiting_transfer` (unchanged, since the loan is still `to_approve` when this fires) |
| Returned (ตีกลับ) | → `to_verify` (officer revises, re-verifies, re-sends) |
| Rejected (ปฏิเสธ, terminal) | → `cancel`, via `_action_do_cancel()` with the approver's reason (no payment exists yet, nothing to void) |
| Cancelled (ยกเลิกการส่ง) / Recalled (ดึงกลับ) | stays `to_approve` — note only, re-sendable |

`_on_sarabun_recalled` is overridden to **not** inherit the mixin's default delegation to `_on_sarabun_returned` — a ดึงกลับ must not move the loan back to `to_verify`.

## Why

- Reusing `to_approve` keeps the loan's own state machine untouched — the bridge is purely a routing concern, matching the pattern already used by `kmitl_project_sarabun` and `budget_transfer_sarabun`.
- A single-step holderless route lets the bridge ship now without pre-deciding who holds the approving position; per ADR-0006 the org-routed chain remains a real future requirement, but building it into Sarabun's route/position configuration is strictly less work than reviving the removed `base_tier_validation` bridge, and doesn't require another code change to this module.
- Negative-outcome mapping mirrors the base module's own semantics: a ตีกลับ is a request for revision (→ `to_verify`, matching `action_reset_to_draft`'s target), a ปฏิเสธ is terminal (→ `cancel`, matching the manual reject/cancel wizard), and a withdrawn send is a no-op on the loan's state (matching how the base module has no state for "not yet re-sent").

## Consequences

- `advance_payment_sarabun` depends on `advance_payment` + `agx_sarabun`; not auto-installed. Installing it changes the approval UX (button swap) but not the underlying `advance.payment` state machine or ACLs.
- `group_advance_payment_loan_officer` additionally implies `agx_sarabun.group_sarabun_user` (create/send documents) once the bridge is installed.
- The manual อนุมัติ button and `group_advance_payment_manager`'s approval power remain in the base module as the fallback path when the bridge is **not** installed; installing the bridge hides that button but does not remove the underlying `action_approve()` guard (still callable programmatically, e.g. by the sarabun completion callback).
- If the org-routed multi-tier chain is required later, it is configured via additional `sarabun.route.template.line` records on `route_template_advance_payment` (or a new template) — no further code change to `advance_payment` or `advance_payment_sarabun` is expected.
