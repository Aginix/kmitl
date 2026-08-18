# Budget transfer approval is routed through e-Saraban; posting is gated on the letter being signed

A budget transfer no longer posts to the ledger the instant a manager clicks *Approve*.
Instead, once the transfer's data is confirmed, an official letter
(*หนังสือขออนุมัติโอนงบประมาณ*, a `sarabun.document`) is issued and routed for
signature through **e-Saraban** (`agx_sarabun`); the transfer posts automatically
only when that letter is signed. The integration lives in a **new bridge module,
`budget_transfer_sarabun`** — the base `budget_transfer` stays installable and
usable without `agx_sarabun`.

## Context

`budget.transfer` (ADR-0013) is a 1:1 delegated `budget.move` of type `entry` — a
**balanced** pure move (`Σfrom == Σto`, `> 0`), reserving/releasing nothing
(ADR-0009). Its lifecycle was `draft → submitted → posted → cancelled`, where
`action_approve` (Budget Manager, not self) re-checked availability and **posted in
the same click** — approval and posting were one step. KMITL wants an e-Saraban
approval to sit *between* "confirm the data" and "post to the ledger": after
confirmation a **สร้างหนังสือ** button issues the letter, it circulates for
signature, and signing auto-posts.

**Scope is deliberately narrow (option A).** The request's umbrella wording
(*การโอนและเปลี่ยนแปลง / ปรับเพิ่ม-ลดงบประมาณ*) names unbalanced operations
(supplementary appropriation / de-appropriation), but those are an **appropriation**
concern, not a transfer (they break the `Σfrom == Σto` premise). This ADR covers the
approval *route* only; increase/decrease is a separate model change, deferred to its
own module and its own grilling.

The bridge follows the proven `sarabun.document.mixin` contract (agx_sarabun
ADR-0004): a consumer overrides `_get_sarabun_*` hooks + `_on_sarabun_*` callbacks
and never re-implements `action_submit_to_sarabun` or `_prepare_sarabun_document_vals`.

## Decision

### Base `budget_transfer` — declares the states, changes nothing else

`budget_transfer` stays a **thin, mostly-untouched base**: this branch's job is the
bridge, not a base rewrite. Odoo requires a `Selection` field to list every value
it may ever hold, so the base gains three new keys — `sent`, `returned`,
`rejected` — plus `sent`/`rejected` in `READONLY_STATES` (field-level lock, which
can't be done from a child module without redeclaring the fields) and `returned`
added alongside `draft` in the view's existing `attrs` (so a returned letter
reopens the whole transfer for revision, matching draft). That is the **entire**
base diff. Nothing else changes: `action_submit`, `action_approve`,
`action_cancel`, `action_reset_to_draft` and `_compute_button_visibility` keep
their original names, bodies and behaviour — the base has no idea `sent`/
`returned`/`rejected` mean anything beyond a locked/unlocked flag; it never
writes them itself, `budget_transfer_sarabun` does.

- `submitted` keeps its name and meaning — ยืนยัน (`action_submit`), the single
  validation checkpoint (`_validate_transfer_data` + availability). The BTR
  number is still minted on leaving `draft`, unchanged.
- `submitted → posted` (**manual approve fallback**, Budget Manager, not self):
  the existing `action_approve`, unchanged. Standalone-usable when no bridge is
  present — draft/submitted/posted/cancelled are the only states a base-only
  install ever reaches.
- `sent`, `returned`, `rejected` are declared but dead weight without the bridge:
  nothing in the base ever writes them, so a base-only environment behaves
  exactly as before.

### New bridge `budget_transfer_sarabun` — owns everything state-specific

`budget_transfer_sarabun` **overrides** (`_inherit` + `super()`) rather than
patches the base — every rule below about `sent`/`returned`/`rejected` lives
here, not in `budget_transfer`:

- `_compute_button_visibility`: calls `super()`, then adds visibility for
  `returned` (Cancel; Reset to Draft for the owner/admin) and `rejected` (Reset
  to Draft for manager/admin, mirroring the base's own `cancelled` gate). `sent`
  is left all-hidden — deal with the live letter (ดึงกลับ/ยกเลิกการส่ง), not the
  transfer form's own buttons.
- `action_cancel` / `action_reset_to_draft`: block outright from `sent` — a live
  letter must be pulled back or voided first, or the transfer and the letter
  states would diverge. `action_reset_to_draft` also gates `rejected` to
  manager/admin before delegating to `super()`.
- `action_approve` / `action_post`: restricted to `submitted` — from `sent` a
  letter is already circulating (approving/posting here would race with
  `_on_sarabun_completed`); from `posted`/`rejected`/`cancelled` it would
  double-post or revive a decided transfer through the back door.
- Its own view (`inherit_id=budget_transfer.view_budget_transfer_form`) adds the
  Returned/Rejected ribbons, extends `statusbar_visible` to include `sent`, and
  hides the `date` field (now synced from the letter's ลงวันที่, see below) —
  none of this touches the base view beyond the `returned`-in-`attrs` change
  above. Separate tree/search view inherits add decorations and filters for the
  three new states.
- `_inherit = ["budget.transfer", "sarabun.document.mixin"]`; depends
  `[budget_transfer, agx_sarabun, budget_transfer_pdf]`; **`auto_install=True`** —
  wherever both `budget_transfer` and `agx_sarabun` are present the integration is
  never silently absent (matches `budget_transfer`'s own auto-install philosophy).
- **สร้างหนังสือ** = the mixin's `action_submit_to_sarabun`, gated by
  `_sarabun_submit_guard → state == "submitted"`. The base manual approve is **kept
  visible** (see Considered options) — from `submitted` a manager sees both buttons.
- **Route wiring via a bridge-owned document *type*, not `origin_model`.** The
  engine resolves a route at send as `route_template_id or type_id.default_route_id`
  (`_seed_route_from_template`); the `origin_model` matcher (`find_matching_templates`)
  is implemented but **never called** — dormant. So the bridge ships:
  1. `sarabun.route.template` "โอนงบประมาณ" with one line — verb **`verb_approve`**
     (อนุมัติ, gating + is_signature), `target_mode=position`, `position_id` = a new
     **`sarabun.position` "ผู้อนุมัติการโอนงบประมาณ" seeded with NO holder**
     (`noupdate`, assign the real approver in Configuration ▸ Positions before
     go-live — the `res.users`-vs-`hr.employee` FK footgun);
  2. `sarabun.document.type` "ขออนุมัติโอนงบประมาณ" (`kind=from_record`) whose
     `default_route_id` is that template;
  3. `_get_sarabun_document_type()` overridden to return that type.
- **Letter content (plain text + งปม. 303 enclosure).** `_get_sarabun_subject` and
  the body are pre-filled; the FROM/TO detail is **not** re-rendered into the letter —
  it rides along as the attached **แบบ งปม. 303** (`budget_transfer_pdf`). Because
  `_prepare_sarabun_document_vals` is mixin-owned, the bridge **wraps**
  `action_submit_to_sarabun` with `super()` and post-processes the created draft:
  sets `content`, and renders `budget_transfer_pdf.action_report_budget_transfer`
  via `ir.actions.report.sudo()._render_qweb_pdf` into an `ir.attachment`
  (`res_model=sarabun.document`) linked through `enclosure_attachment_ids`
  (สิ่งที่ส่งมาด้วย). The pre-filled `content` remains editable by ธุรการ before send.
  - subject: `ขออนุมัติโอน เปลี่ยนแปลง {source complete_name} ประจำปีงบประมาณ พ.ศ. {fiscal year} {department complete_name}`
  - body: `ด้วย{department} มีความประสงค์ขออนุมัติโอน เปลี่ยนแปลง {source} ประจำปีงบประมาณ พ.ศ. {fy} จำนวนเงิน {amount} บาท รายละเอียดตามเอกสารแนบ แบบ งปม. 303 เลขที่ {BTR}`
- **`_get_sarabun_report_action → False`** — the letter uses the default e-Saraban
  body (plain text + endorsement/signature block); no custom transfer report.
- **Callbacks (bridge):**
  - `_on_sarabun_circulating` → `submitted`/`returned` become `sent`.
  - `_on_sarabun_completed` → **auto-post** the transfer, and stamp
    `approver_id = document._signature_steps()[-1:].acted_by_id` (the final signer,
    empty-safe) and `approval_date = document.signed_at`.
  - `_on_sarabun_returned` (ตีกลับ) / `_on_sarabun_recalled` (ดึงกลับ) → `returned`.
  - `_on_sarabun_rejected` (ปฏิเสธ, terminal) → `rejected`; **never posts**.
  - `_on_sarabun_cancelled` (ยกเลิกการส่ง) → `submitted`; the letter's number is
    voided, the transfer is ready to issue a fresh letter.

### No availability re-check at completion (for now)

`_on_sarabun_completed` posts **without re-validating** availability — it trusts the
`draft → submitted` check. A transfer reserves nothing (ADR-0009), so its source
budget is **not locked while the letter circulates**; between confirm and signature
another document could consume it, and the transfer could post the source below zero.
We accept this window rather than block the final signer, because the real fix is to
route transfers through **budget reservation** (an *ใบจอง*), which is **deferred**
(see Consequences). Callbacks run in the signer's transaction and a raise rolls their
action back (ADR-0004); we keep the completion callback non-raising.

### Rollout

`budget_transfer` is **pre-production** (only just split out in #1097): the
existing `submitted` state is kept and extended in place with `sent`/`returned`/
`rejected` — **no version bump, no migration** (transfer records ≈ 0). The
bridge is a fresh install.

## Considered options

- **Hide the manual approve when the bridge is installed** (the `kmitl_project` /
  `agx_approval_sarabun` pattern). Rejected: KMITL has only **two** Budget Managers,
  tightly controlled, and wants the direct approve-and-post as a sanctioned escape
  valve alongside the letter — not every transfer needs to wait for e-Saraban.
- **Wire the route by `origin_model` on the route template** (what
  `agx_approval_sarabun` ships). Rejected: verified dormant — nothing calls
  `find_matching_templates`, so such a route never seeds and `action_send` would
  raise "add a gating step". Wiring through the document type's `default_route_id`
  is the only live path. (`agx_approval_sarabun`'s route is latent for this reason —
  a cautionary precedent, not one to copy.)
- **A custom e-Saraban report reproducing the FROM/TO table.** Rejected: the letter
  is a plain-text *บันทึกข้อความ* that *references* the supporting form; the FROM/TO
  detail already exists as **แบบ งปม. 303** (`budget_transfer_pdf`) and is enclosed,
  avoiding a second FROM/TO renderer and the kmitl_project half-baked-report crash.
- **Re-check availability at completion and block (raise), or land in a special
  "post-failed" state.** Rejected *for now*: blocking punishes the final signer for a
  race they didn't cause; a special state adds a lifecycle branch. Both are stop-gaps
  for the missing reservation — so we defer to the reservation decision instead.
- **Fold e-Saraban directly into `budget_transfer` (no bridge).** Rejected: the user
  asked for a new module, and the base must stay installable where `agx_sarabun`
  isn't present (`budget_transfer` is `auto_install=True` on every budget env).

## Consequences

- **Posting is now event-driven.** A transfer reaches `posted` either by the manual
  fallback (manager click) or by the letter being signed — two paths to the same
  ledger effect. The delegated `budget.move` still posts exactly once, at that moment.
- **Open race until reservation exists (deferred, revisits ADR-0009).** Source budget
  is unlocked while the letter circulates. The clean fix — put transfers through a
  reservation/*ใบจอง* the way commitments are — is parked as a follow-up; it would
  close the window and make the completion re-check moot. Until then, treat a
  submitted-but-unsigned transfer as *not yet holding* its source budget.
- **Dead code left as-is (out of scope for this branch).** The base now has a
  real `rejected` state, reached via the letter's ปฏิเสธ — but only when the
  bridge is installed. The pre-split standalone reject wizard (which already
  wrote a non-existent `state="rejected"` + `rejection_reason` before this ADR,
  and is not imported by the module) stays untouched; this branch's job is the
  bridge, not a `budget_transfer` cleanup. Removing or repurposing it is a
  separate, dedicated change.
- **agx_sarabun unchanged.** The bridge lives entirely within the current mixin
  contract; the `origin_model` auto-matcher stays dormant (out of scope to wire).
- **budget_transfer version stays 16.0.1.0.0** (pre-production). When the module goes
  live, a normal bump applies — no state remap needed, since `submitted` was never
  renamed.
