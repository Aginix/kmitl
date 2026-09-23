# Approval-gated project lifecycle routed through e-Saraban

A `kmitl.project` no longer goes live on a one-click Confirm (`draft→new`). It now passes an **approval front that mirrors `agx_approval`** — `draft → to_verify → to_send → sent → in_progress → complete` — where the ขออนุมัติจัดโครงการและค่าใช้จ่าย is a หนังสือ routed through e-Saraban. The old `new`, `approved` and `on_hold` states are gone (`approved` is folded into `in_progress`; `on_hold` is dropped). Base `kmitl_project` owns every state and the forward/reset/cancel transitions plus a **manual approve fallback**; a new bridge **`kmitl_project_sarabun`** (`_inherit = ["kmitl.project", "sarabun.document.mixin"]`) adds *สร้างหนังสือ* (`action_submit_to_sarabun`) and the `_on_sarabun_*` callbacks that drive the หนังสือ-based transitions. This is the same pattern as `agx_approval` + `agx_approval_sarabun` (integration contract: agx_sarabun ADR-0004).

## The lifecycle

Forward (creator-driven, self-service):
- **`draft → to_verify`** — "ยืนยัน". Runs `detect_exceptions()` and pops the blocking-exception wizard (this is where the strategic-plan-completeness rule is finally enforced — see Consequences).
- **`to_verify → to_send`** — "จองงบประมาณ", a **single action** that mints the Project Number (`key`), creates the analytic account, and **reserves one new `budget.commitment`** for the full `budget_amount` from the floating project pool (always reserve-new; never draw-existing, unlike `agx_approval`).
- **`to_send → sent`** — "สร้างหนังสือ" (`action_submit_to_sarabun`); `_on_sarabun_circulating` flips `to_send→sent`. *Base fallback without the bridge:* a manual approve moves `to_send → in_progress` directly.
- **`sent → in_progress`** — **automatic** when the หนังสือ is signed (`_on_sarabun_completed`). Execution starts immediately; there is no idle "approved" resting state.
- **`in_progress → complete`** — manual; does **not** auto-return leftover reserved budget.

Negative paths (all fire while `sent`, via bridge callbacks):
- **ตีกลับ / ดึงกลับ → `returned`** (`_on_sarabun_returned`; recall forwards to it by mixin default). Budget **kept**; project **fully editable**; "ส่งใหม่" re-creates/re-sends the หนังสือ (`returned→sent`) and **re-checks/adjusts the reservation** if `budget_amount` changed.
- **ปฏิเสธ → `rejected`** (`_on_sarabun_rejected`). Budget **released**. Revive via Reset to Draft.
- **ยกเลิกการส่ง → `to_send`** (`_on_sarabun_cancelled`). Budget **kept**; the voided หนังสือ is replaced by a fresh one. Not terminal for the project.

Cross-cutting:
- **Reset to Draft** (releases any reservation): `to_verify, to_send, returned, rejected, cancel → draft`. Blocked from `sent` (deal with the หนังสือ first) and from `in_progress` (no un-approving an executing project).
- **Cancel** (manager; releases the reservation only while untouched, keeps it once any obligate/consume exists — budget ADR-0007): `draft, to_verify, to_send, returned, rejected, in_progress → cancel`. **Blocked from `sent`** (a project must not be cancelled while its หนังสือ is circulating) and from `complete`.

## Why

- **Real KMITL process.** A project must be *formally approved to run and to spend* before it may execute; the old one-click `draft→new` had no authorization gate at all. The หนังสือ is that authorization.
- **Reuse a proven front, don't invent one.** `agx_approval`'s states and Thai labels are already exactly this chain (`to_verify` = "รอตรวจสอบ / จองงบประมาณ", …), and `agx_approval_sarabun` already wires the bridge. Mirroring it gives a consistent UX and rides the hardened, tested callback contract (ADR-0004) instead of a bespoke one.
- **Reserve before approval, release on reject.** Securing the budget *before* raising the หนังสือ lets the approval show the money is already set aside; releasing it on ปฏิเสธ keeps rejected projects from pinning the floating pool.
- **The project is the approvable entity.** Carrying the approval states on `kmitl.project` itself is cleaner than spawning a separate `approval.request` — the thing being approved *is* the project.
- **No idle post-approval state.** Approval means "go": the project can raise purchase requests and disbursements the instant the หนังสือ is signed, so a distinct `approved` resting state would only ever be a blink — fold it into `in_progress`.

## Consequences

- **Supersedes the reserve *trigger* of budget ADR-0007.** Reservation moves from `draft→new` to the `to_verify→to_send` "จองงบประมาณ" step. ADR-0007's floating-budget model otherwise stands: still one shared commitment for the full `budget_amount`, drawn down by the project's purchase requests and disbursements.
- **Revises the mint *trigger* of ADR-0001.** `key` + analytic account are now minted at `to_verify→to_send`, not `draft→new`. Everything else in ADR-0001 (key carries the Project Number, fiscal-year stamping, sticky across reset-to-draft, รหัสโครงการ still deferred) is unchanged.
- **Fixes an exception-bypass bug found on review.** The old Confirm called `button_new`, skipping `detect_exceptions()`; the sole rule (a Strategic Project must align to all four strategic-plan levels) was never enforced — doubly so because `models/kmitl_project_exception.py` was never imported by `models/__init__.py`, so the `base.exception` layer was not even registered. The file is now imported and the check runs at "ยืนยัน" (`draft→to_verify`). It deliberately drops the OCA `main_exception_id asc` `_order` so project lists keep their existing newest-first ordering.
- **New module `kmitl_project_sarabun`** (`depends: ["kmitl_project", "agx_sarabun"]`). Base stays standalone-usable/testable via the manual approve fallback; `sent`/`returned`/`rejected` exist in the base Selection but are only reachable with the bridge installed.
- **`returned` is fully editable including `budget_amount`**, so re-sending must re-check availability and adjust the reserved commitment to the new amount.
- **`complete` does not auto-return leftover reserved budget** (deliberate, per stakeholder) — the user returns it manually; contrast budget ADR-0009. This is an open point if that policy changes.
- **Roles are creator-driven and provisional.** The creator performs ยืนยัน + จองงบ + สร้างหนังสือ self-service (no separate verifier), with cancel/reset leaning on the manager group. Still to be validated with real users.
- **Downstream consumers gate on `in_progress`.** A พ.1 may only be raised from an *approved* project, so `kmitl_project_purchase_request` now requires `in_progress` (it used to accept `new`) and no longer advances the project itself — the หนังสือ does. Same for what the portal publishes and what the department dashboard counts: the approval band (`to_verify`…`sent`) and `rejected` are excluded. Note the gate is **approval, not the absence of money**: the reservation is minted at `to_verify → to_send`, so a project sitting at `to_send`/`sent`/`returned` already holds a live commitment that `_release_project_commitment` does not cancel. Every entry point must therefore assert `in_progress` itself — including the draw-down picker, which offers a slip without going through this project's own create-PR button (budget [ADR-0015](../../../budget/docs/adr/0015-pr-draws-only-source-backed-reservations.md)).
- **Built** in `kmitl_project` 16.0.2.0.0 (state remap `new→in_progress`, `on_hold→draft` in `migrations/16.0.2.0.0/pre-migration.py`) plus the new `kmitl_project_sarabun`.
