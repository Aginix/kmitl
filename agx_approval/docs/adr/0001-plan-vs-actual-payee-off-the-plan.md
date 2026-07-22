# Split the expense request into a plan and a post-mission actual; keep the payee off the plan

An expense-approval request now models **two moments of one activity**: the *plan* (ค่าใช้จ่าย broken down by expense type + a participant roster), captured and approved before the money is spent; and the *actual expense allocation* (recipient × product × actual amount × bank), recorded after the mission and billed into a disbursement. The plan deliberately carries **no payee** — at approval time nobody yet knows who will สำรองจ่าย / ยืมเงิน, so the recipient is a participant chosen only when actuals are recorded. Approval is routed through **e-Saraban** (the request spawns a หนังสือ whose outcome drives the request's state), and `payment_type` is removed from the form because advance-vs-direct is not known at approval.

## Considered options

- **Payee per expense line (status quo).** Rejected: UAT couldn't name a recipient up front, and it forced exactly one payee on every expense row.
- **งบหน้าใบสำคัญคู่จ่าย as a separate document, now.** Deferred: it is a full document (per-person itemisation, withholding-tax, ผู้ทดรองจ่าย, PDF, dean signature). Its *data* is captured in the actual-allocation table on the request; only the formal PDF is deferred.
- **Single recipient at billing.** Rejected: real reimbursements pay several recipients, and a disbursement line needs *both* a product and a partner — so multi-recipient forces the per-recipient breakdown to live on the request (the "งบหน้า data") rather than being derivable from a payee-less plan.

## Consequences

- **New state machine** (see [`docs/approval-state-machine.drawio`](../approval-state-machine.drawio)): `draft` → `to_verify` (รอตรวจสอบ/จองงบ) → `submitted` (รอส่งขออนุมัติ) → `sent` (สารบรรณเวียน) → `approved` → `actual` (บันทึกจริง) → `billed`; plus `rejected` / `returned`. `ready_to_bill` and the `payment_type` branch are dropped.
- Approval / reject / return arrive from e-Saraban callbacks (`_on_sarabun_circulating` → sent, `_on_sarabun_completed` → approved, `_on_sarabun_rejected` → rejected, `_on_sarabun_returned` → returned, `_on_sarabun_cancelled` → submitted). `agx_approval_sarabun` is rewired to the rebuilt engine's contract (override `_get_sarabun_subject`, not `_prepare_*`) and gets a new route template for the sign-off chain.
- **D1** pull-back (ดึงกลับ) in `to_verify`/`submitted` → `draft` via a confirm wizard, releasing the reservation; distinct from e-Saraban's own ดึงกลับ on a circulating หนังสือ.
- **D2** a Sarabun-returned request is editable everywhere **except budget**, then re-sent.
- **D3** a single `returned` state; edit surface is computed by lifecycle — pre-bill (Sarabun return) = all-except-budget; post-bill (DR return) = the three clerical fields of `agx_approval_disbursement` ADR-0001.
- **D4** e-Saraban ยกเลิกการส่ง → back to `submitted` (reservation kept, a fresh หนังสือ can be created). **D5** reject → `rejected` + release reservation, treated as terminal (redo by resetting to `draft`).
- **D6** `payment_type` removed; borrowing money (`advance_payment`) becomes a post-approval action; the disbursement bridge stops branching on `payment_type`.
- The `actual_amount` wizard is replaced by an inline allocation table; the auto-derived `payee_ids` and per-line `partner_id` are removed; both PDF reports (`agx_approval`, `agx_approval_sarabun`) re-render as a flat plan table + participant roster + per-recipient actuals.
- This is a cross-module epic: `agx_approval`, `agx_approval_sarabun`, `agx_approval_disbursement`, `agx_approval_advance_payment`.
- **Per-ส่วนงาน approval route:** each department differs, so there is no single hard-coded chain — the route is seeded from a `sarabun.route.template` scoped by `department_id` (+ optional `condition_domain`), resolved at send time from the requester's department via the engine's `find_matching_templates`.
- **Pre-production (UAT):** the module is not yet live, so the `partner_id` / `payee_ids` removals and the restructure are applied in place — no data migration, no manifest version bump.
- The formal งบหน้าใบสำคัญคู่จ่าย PDF (`report_disbursement_voucher`) renders the allocation grouped per recipient × expense type with withholding-tax columns and the dean's signature. Each recipient advances/borrows for themselves, so there is no single ผู้ทดรองจ่าย.
