# agx_sarabun Rebuild — Implementation Plan

> **Status:** greenfield rebuild. The module is **not in production**, so there is no data migration and no backward-compat shim — we **wipe and rebuild** the `agx_sarabun` codebase. The one hard constraint is that **all 5 in-repo consumers must be migrated** to the new adapter contract in the same change set (ADR-0004), because they import `sarabun.document.mixin` and will break the moment the old models are deleted.
>
> **Authoritative sources (read first, they win on any conflict):**
> - `agx_sarabun/CONTEXT.md` — canonical glossary. Use these terms exactly; honour every _Avoid_.
> - `docs/adr/0001-routing-engine-dynamic-chain.md` — Route is living data on one `sarabun.routing.step` entity; templates only seed.
> - `docs/adr/0002-document-lifecycle-negative-paths.md` — full lifecycle + voided numbers.
> - `docs/adr/0003-position-catalog-not-hr-job.md` — `sarabun.position` catalog, holder snapshot.
> - `docs/adr/0004-integration-adapter-contract.md` — hardened callback-push, atomic, 1:N.

---

## 0. Naming, identity, and what dies

### Identity
A true **e-Saraban** (official correspondence) system. The **หนังสือ (Document, `sarabun.document`) is the protagonist**. The **approval-routing engine** is the emphasised, embedded core. Other modules attach as **origin records** through a secondary adapter. **v1 focuses on the `from_record` kind** (origin-driven e-flow) — `memo`/`circular` ride the same engine, but their manual-compose UX is phase-2.

### Models that are DELETED (old → replacement)
| Old model | Fate |
|---|---|
| `sarabun.routing.line` (plan) | **Merged** into `sarabun.routing.step` |
| `sarabun.document.recipient` (tracker) | **Merged** into `sarabun.routing.step` |
| `sarabun.role` (+ `role_category`) | **Replaced** by `sarabun.position` catalog (ADR-0003); academic rank is display-only, never a target |
| `sarabun.reference` (hardcoded PR/PO/budget link) | **Dropped** — that was *related ERP records* (the origin link already covers it); อ้างถึง is a new m2m+free-text construct |
| per-consumer `main_sarabun_document_id` | **Dropped** — mixin owns `sarabun_document_ids` + `active_sarabun_document_id` |
| `read()` override notification anti-pattern | **Deleted** — replaced by `mail.activity` + bus |
| `sarabun.route.template` / `.line` | **Demoted** to seed-only (kept, but no longer the source of truth for the flow) |

### Models that are NEW or substantially reshaped
- `sarabun.document` — reshaped (lifecycle, header fields, kind split, immutable signed copy).
- `sarabun.routing.step` — **new single routing entity** (target + verb + state + outcome).
- `sarabun.position` — **new** administrative-position catalog with holders.
- `sarabun.document.type` — kept but re-rooted: an admin record binding (kind × sequence × default route × template).
- `sarabun.document.kind` — fixed dev-extensible behaviour axis (modelled as a `Selection` on type, see §Phase 1).
- `sarabun.register` / sequence resolution — reshaped for (ส่วนงาน × type) own-register, atomic allocation, voided gaps.
- `sarabun.document.mixin` — hardened adapter (ADR-0004).
- `sarabun.document.reference` (อ้างถึง) + `sarabun.document.enclosure` (สิ่งที่ส่งมาด้วย) — new ordered/described line models.

---

## 1. Phased build order

Each phase is a self-contained, installable, testable increment. Dependencies flow strictly downward; later phases never force a rewrite of an earlier one. **Every phase ends with its tests green** (§2).

```
P1 Core data model ─┐
                    ├─> P2 Routing engine + lifecycle state machine ─┐
P1.5 Position ──────┘                                               ├─> P5 Signing / freeze / cover sheet
                                                                    │
                    P3 Numbering / register ────────────────────────┤
                                                                    │
                    P4 Notifications + access/record-rules ─────────┤
                                                                    │
                                    P6 Adapter + migrate 5 consumers ┘
                                    P7 Tests (woven through, hardened at end)
```

### Phase 1 — Core data model (document + type/kind + references/enclosures + position)
**Rationale:** everything hangs off the หนังสือ and its classification. Build the static skeleton before any behaviour so later phases have stable fields to attach to. Position is built here too (it is a leaf catalog with no dependencies) so Phase 2 can target it.

**Deliverables**
- `sarabun.position` (ADR-0003): `name` (Thai), `code`, `parent_id` (org hierarchy), `holder_ids` (m2m → `hr.employee` or `res.users` — resolve at §1.5 decision below), `sequence`/active. **No** coupling to `hr.job` or academic rank. Method `_resolve_holders()` returning the current person-set (used by the engine at step-activation to snapshot).
  - **Decision to lock in P1:** holders point at `hr.employee` (so the signature block can read `academic_standing_title` + digitized signature), and `res.users` is derived via `employee.user_id`. A Position with a holder lacking a `user_id` must still be addressable (this is the old bug — see P4 access).
- `sarabun.document.type` (admin-configurable): `name`, `kind` (Selection: `memo`/`circular`/`from_record`; dev-extensible, phase-2 adds `external`/`order`/`announcement`), `sequence_resolution` link (filled in P3), `default_route_template_id` (filled in P2), `report_template`/compose hooks. **Kind and type are two fields** — never reuse a hardcoded `code` selection as both behaviour key and identifier (the old bug).
- `sarabun.document` core fields (no behaviour yet):
  - Header: `subject` (เรื่อง), `addressee` (เรียน — **own field**, manual/origin-set), `addressee_through` (ผ่าน — free text). Drop the old free-text `recipient`/"To".
  - Classification: `type_id` (→ kind), `secrecy_label` (display-only in v1).
  - Origin link (1:N side lives here): `origin_model`, `origin_res_id` (+ index).
  - References: `reference_document_ids` (m2m self → prior `sarabun.document`) + `reference_line_ids` (free-text out-of-system letters) = อ้างถึง. **Do not** recreate `sarabun.reference`.
  - Enclosures: `enclosure_ids` (`sarabun.document.enclosure`: `sequence`, `name`/description, `attachment_id`) = สิ่งที่ส่งมาด้วย, rendered as a numbered list.
  - Lifecycle field placeholder `state` (values stubbed; the machine is P2).
- `mail.thread` / `mail.activity.mixin` inheritance on the document.

**Phase-2 seams to leave in place**
- `sarabun.position.acting_ids` field reserved (commented contract) for รักษาการ/มอบอำนาจ — v1 resolves only `holder_ids`.
- `kind` Selection extension point documented (external/order/announcement land later).
- `secrecy_label` is a label only; no domain/record-rule enforcement (P4 note).

---

### Phase 2 — Routing engine + lifecycle + state machine
**Rationale:** the heart of the system and the project's emphasis (ADR-0001). It depends on P1's document + position. Build the single step entity, the stage/concurrency rules, the dispositions, and the document lifecycle together because they are one coupled state machine.

**Deliverables**
- `sarabun.routing.step` — **the single routing entity** (replaces line+recipient):
  - `document_id`, `order` (Stage = steps sharing one order), `sequence`.
  - **Target** (exactly one mode): `target_mode` ∈ {`position`, `person`, `unit`} → `position_id` / `user_id` / `department_id`. Canonical = Position. _Avoid_ the old `recipient_type` "user/department/role" vocabulary.
  - `snapshot_holder_ids` — the resolved person-set, **written when the step becomes active** (Position/Unit → current holders), never recomputed.
  - **Verb** (3): `verb` ∈ {`acknowledge` (รับทราบ, non-gating), `endorse` (เห็นชอบ, gating), `sign_approve` (ลงนาม-อนุมัติ, gating, carries signature)}.
  - `for_info` boolean → สำเนาเรียน (a non-gating `acknowledge` step flagged for CC; **not** a separate entity).
  - **State**: `waiting` → `active` → (`done` | `returned_from` | `rejected_at`) — step-level.
  - **Outcome**: `actor_id` (who actually acted), `acted_at`, `capacity_position_id` (the Position they signed in), `note` (the เกษียน comment), `disposition`.
- **Dispositions (5)** as engine actions on an active step, gated by authority (actor ∈ snapshot set):
  - `complete` — perform the verb.
  - `direct` (เกษียนสั่งการ) — complete + **insert the NEXT step(s)** at runtime. First-class, common path.
  - `delegate` (มอบหมาย) — reassign **THIS** step's actor to X (X acts instead). **Distinct from direct.**
  - `return` (ตีกลับ) — send back; destination **choosable** (default: sender + restart chain; or resume from a picked step). Lands document in `returned`.
  - `reject` (ปฏิเสธ) — terminal negative.
- **Stage / concurrency rules** (CONTEXT §Concurrency):
  - A Stage advances when **every gating step** (endorse / sign_approve) in it is positively `done`.
  - `acknowledge` steps **never block** advancement or completion; pending ones are tracked only ("ค้างรับทราบ N").
  - Multi-holder Position/Unit step = **first-to-act-wins** (first holder completes it for the group). "Everyone must act" = multiple parallel steps, never a quorum flag.
  - **One `reject`** in a co-approval stage rejects the whole document immediately.
- **Document lifecycle** (ADR-0002), `state`: `draft → circulating → completed`; negatives `returned`, `rejected`, `cancelled`.
  - `circulating` renamed from old `sent`.
  - `returned` is revisable (prior chain kept as history).
  - `rejected` is terminal → proceed by **duplicating to a NEW draft** (preserve audit that *this* doc was rejected). Implement `action_duplicate_to_draft()`.
  - `cancelled` = เรียกคืน Recall, allowed **only before any `sign_approve` step has occurred**. The engine must **track the strongest verb completed so far** (helper `_highest_verb_done()`), not just `state`. After a signature exists, recall is blocked → user issues a cancellation หนังสือ (manual, phase-2 compose).
- **act-on-step API**: a single backend service method `action_act_on_step(step, disposition, **kw)` that is the one entry point for all dispositions. **Design it token-ready** (accept an optional `act_token`/actor resolution layer) so phase-2 magic-link acting drops in without reshaping the API.
- **Route Template** seeding only: `sarabun.route.template` + `.line` kept, but `_seed_steps_from_template()` copies lines → `sarabun.routing.step` rows at send. The template **does not own or constrain** the flow after seeding (ADR-0001).
- **Semantic helpers** on the document, consumed by Phase 6: `is_draft`, `is_circulating`, `is_completed`, `is_returned`, `is_rejected`, `is_cancelled`. These replace all hardcoded `state == "sent"` reads.

**Phase-2 seams to leave in place**
- `action_act_on_step` accepts (but ignores in v1) an `act_token` param → magic-link acting.
- `delegate`/`direct` authority check has a hook point where รักษาการ/มอบอำนาจ acting capacity will later be honoured; v1 only checks membership in `snapshot_holder_ids`.

---

### Phase 3 — Numbering / register
**Rationale:** the official number is assigned **at send** (draft → circulating), so the register depends on P2's lifecycle transition being in place. Isolated as its own phase because it carries the highest data-integrity stakes (atomicity, voiding, per-unit registers).

**Deliverables**
- **ลงทะเบียน (Register)** kept as a **distinct event** fired automatically inside the draft→circulating transition (so a phase-2 clerk gate can intercept it).
- **Sequence resolution from (sender ส่วนงาน × type)** — each ส่วนงาน issues from **its own register**, not an institute-wide pool. Configuration model binds (department, document.type) → sequence.
- **Block send with a clear error** if no sequence is configured for that (unit × type) — never silently number from a default.
- **Atomic allocation** — **FIX the old `max()+1` Python race**:
  - Row-lock the register row (`SELECT … FOR UPDATE`) during allocation.
  - Backstop unique constraint `unique(sequence, number, year)`.
  - Retry-on-conflict loop.
- **Reset per ปีงบประมาณ** (fiscal year Oct–Sep) by default; render in **พ.ศ.**
- **Voided number (เลขยกเลิก)** — when a numbered document becomes `rejected`/`cancelled`, the number is **voided: permanent gap, never reissued**, recorded as ยกเลิก in the register.
- Keep **reserved / gap / manual** numbering modes for manual compose only (memo/circular).

**Phase-2 seams to leave in place**
- Register event exposes a pre-assign hook → phase-2 **สารบรรณกลาง clerk register gate** intercepts here.
- Manual/reserved modes wired but only surfaced for manual-compose kinds (which are themselves phase-2 UX).

---

### Phase 4 — Notifications (mail.activity + inbox/systray) + access / record-rules
**Rationale:** depends on P2 (active step = trigger) and P1 (position holders = who to notify / who can see). Grouped because both "who gets pinged" and "who can read" derive from the same snapshot-actor set.

**Deliverables**
- **REMOVE the old `read()`-override anti-pattern** entirely (it wrote to the DB inside `read()`, keyed on a brittle "subject in fields" heuristic). It does not come back in any form.
- **mail.activity** "action required" scheduled on the **active step's actor(s)** (the snapshot holders' `user_id`s):
  - Multi-holder step → notify **ALL** holders.
  - When one acts (first-to-act-wins), **auto-clear the others' activities**.
- **Sarabun inbox / systray tray** (lightweight) + **bus** realtime push (keep `bus` dep; reuse the ting sound asset if desired). Rebuild the systray as an OWL component listing the user's active-step documents.
- **Access / record-rules (Route visibility, CONTEXT §Access):**
  - Readable by: the **sender**, plus snapshot actors of any step that is **`active` or `done`**.
  - Steps `waiting`/future grant **NO** visibility, even if pre-seeded with a named person.
  - **Acting** permitted only to the actor of an **active** step.
  - **FIX the old bug**: Position/Unit targets with no `user_id` could not see the document. Record rule keys off the **snapshot holders' users** (resolved at activation), not a raw `recipient_ids.user_id`.
  - **Manager-see-all stays** in v1.

**Phase-2 seams to leave in place**
- `ชั้นความลับ` **need-to-know enforcement is phase-2** — v1 keeps `secrecy_label` as a display label only; no record-rule narrowing. Leave a clearly-marked extension point on the read rule.
- Notification layer is backend-first; the activity payload carries the step id so a phase-2 **magic-link** email can deep-link to the act-on-step API.

---

### Phase 5 — Signing / freeze / cover sheet
**Rationale:** terminal-state behaviour; depends on the lifecycle reaching `completed` (P2), the register number (P3), and the signature data (P1 position + employee fields). Built late because it consumes everything upstream.

**Deliverables**
- **Signature block**: signer name + academic prefix (`hr.employee.academic_standing_title`) + **Position signed in** (`capacity_position_id` on the sign step) + **digitized signature image** (`hr_employee_digitized_signature` module — add to manifest `depends`) + datetime.
- **เกษียน trail rendered onto the official document** (who / when / capacity / comment) — **not** hidden in chatter.
- **ใบปะหน้าสารบรรณ (Cover sheet)** for `from_record`: system-rendered front page (header number / date / เรื่อง / เรียน / ผ่าน + signature block + เกษียน trail), **MERGED** with the **origin's report (the body)** into one PDF.
- **Freeze ฉบับลงนาม**: at `completed`, render once and **freeze an immutable PDF** as an attachment. After freeze, portal/print **serve the frozen file**; before completion, preview **renders live** (own report or delegated origin report).
- Portal controller + template rebuilt to serve frozen-vs-live correctly.

**Phase-2 seams to leave in place**
- **Full memo/circular compose template** (reformatting origin content into a บันทึกข้อความ body) is **deferred** — v1 merges cover sheet + origin report only.
- **PKI / cryptographic signing** is a seam: the freeze step produces a plain PDF; leave a hook (`_sign_pdf(pdf_bytes)` no-op) where a phase-2 PKI signer slots in.

---

### Phase 6 — Adapter + migrate the 5 consumers
**Rationale:** the new mixin contract (ADR-0004) can only be finalised once the engine, lifecycle, and step entity exist. Migrating the consumers must land **in the same change set** as deleting the old models, or the repo won't install. See §3 for the per-module checklist.

**Deliverables**
- `sarabun.document.mixin` hardened (ADR-0004):
  - **Owns the origin↔document relation** via `origin_model`/`origin_res_id` (on the document). Exposes `sarabun_document_ids` (all) + `active_sarabun_document_id` (current live), replacing per-consumer `main_sarabun_document_id`.
  - **Callbacks**: `_on_sarabun_completed(document)`, `_on_sarabun_rejected(document)`, `_on_sarabun_returned(document)`, `_on_sarabun_cancelled(document)`, plus generic `_on_sarabun_step(step, disposition)`. **Every callback receives a `sarabun.routing.step`** (or the document), **never** a `sarabun.document.recipient`.
  - A sanctioned **circulating** reaction hook (replacing the old `_on_sarabun_sent` monkey-patch) — either `_on_sarabun_circulating(document)` or fold into `_on_sarabun_step`.
  - **Atomic / fail-loud**: callbacks run in the **actor's transaction**; a failing origin callback **rolls back the action** (no `try/except` swallow, no `sudo()` safety net). Origins that must proceed despite a failing callback opt in explicitly (deferred).
  - `action_create_sarabun_document()` and `_prepare_sarabun_document_vals()` retained; report-delegation hooks `_get_sarabun_report_action()` / `_get_report_base_filename()` retained (origin report becomes the **body** under the cover sheet).
- **Migrate all 5 consumers** per §3.

**Phase-2 seams to leave in place**
- **Incoming ทะเบียนรับ** (inbound register, Unit-targeted documents) — the `unit` targeting mode and central-registry concept exist, but the inbound-receipt workflow is phase-2.
- Per-step callback `_on_sarabun_step` is available now but consumers adopt it opportunistically (replaces old `_on_sarabun_action`).

---

### Phase 7 — Tests (hardened)
Tests are written **inside each phase** as it lands; Phase 7 is the final hardening pass (integration scenarios, negative paths, race conditions). See §2.

---

## 2. Testing strategy

Tests live in `agx_sarabun/tests/` (and per-consumer `tests/` for migration), with `__init__.py` importing each test module. Use `@tagged("post_install", "-at_install")` so all dependencies (hr, mail, the 5 consumers) are installed.

### Mixin / abstract-model testing (CLAUDE.md TransientModel pattern)
`sarabun.document.mixin` is abstract (no table). To test it, define a `TransientModel` in the test file and register it dynamically in `setUpClass`:

```python
from odoo import fields, models
from odoo.tests.common import TransactionCase, tagged


class SarabunMixinTestModel(models.TransientModel):
    _name = "test.sarabun.origin"
    _description = "Test Origin"
    _inherit = "sarabun.document.mixin"

    name = fields.Char()
    # expose the callbacks under test as overridable spies


@tagged("post_install", "-at_install")
class TestSarabunMixin(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        SarabunMixinTestModel._build_model(cls.registry, cls.cr)
        cls.registry.setup_models(cls.cr)
        cls.registry.init_models(
            cls.cr, ["test.sarabun.origin"], {"module": "agx_sarabun"}
        )
        cls.Origin = cls.env["test.sarabun.origin"]
```

Use this for: the mixin's `sarabun_document_ids`/`active_sarabun_document_id` computes, callback dispatch (`_on_sarabun_*` invoked with a `sarabun.routing.step`), and the rollback-on-callback-failure guarantee.

### Coverage by phase
- **P1 data model:** type↔kind separation (two fields, not one); position holder resolution; อ้างถึง m2m + free-text lines; enclosure ordering/numbering.
- **P2 engine (the bulk):**
  - Stage advances only when all **gating** steps done; `acknowledge` steps never block advancement or completion.
  - First-to-act-wins on multi-holder Position/Unit; one `reject` in a co-approval stage rejects the whole document.
  - Each disposition: `complete`, `direct` (inserts NEXT step), `delegate` (reassigns THIS step), `return` (default back-to-sender + restart **and** resume-from-picked-step), `reject` (terminal).
  - **Delegate ≠ Direct** asserted explicitly.
  - Lifecycle transitions incl. negatives; `returned` keeps prior chain as history; `rejected` → `action_duplicate_to_draft` creates a new linked draft; recall allowed before any `sign_approve`, **blocked after** (assert `_highest_verb_done` gate).
  - Snapshot immutability: change a Position's holders after activation → step's `snapshot_holder_ids` unchanged.
- **P3 numbering:**
  - Per-(unit × type) register isolation; **send blocked with clear error** when unconfigured.
  - **Race test**: concurrent allocation (two cursors / two threads) → no duplicate number; assert the row-lock + unique-constraint backstop hold (this is the explicit regression test for the old `max()+1` bug).
  - Voided number → permanent gap, never reissued; fiscal-year reset; พ.ศ. rendering.
- **P4 access/notify:**
  - Record-rule: sender + active/done snapshot actors can read; waiting/future steps grant **no** read even with a named person.
  - **Regression**: Position/Unit holder with no `user_id`… ensure the document is reachable and (where a user exists) visible — the old hide bug.
  - Activity scheduled on all holders; first-to-act auto-clears the others'.
  - Assert the `read()`-override anti-pattern is **gone** (no DB write inside read).
- **P5 signing:** cover sheet merges with origin report; freeze produces an immutable attachment; post-freeze portal/print serve the frozen file, pre-completion preview renders live; signature block fields present.
- **P6 adapter:** callback dispatch with a `sarabun.routing.step`; **rollback test** — a consumer callback that raises must roll back the actor's disposition (nothing committed in either model).
- **P7 integration scenarios (end-to-end):** PR → submit → seed route → endorse → sign-approve → completed → origin `button_approved`; reject path → origin `button_rejected` + duplicate-to-draft; return path; recall path. One scenario per consumer (§3).

---

## 3. Consumer migration checklist

> All 5 modules import `sarabun.document.mixin`. The shared edits below apply to every mixin consumer; per-module subsections list the exact edits. Migration lands **in the same change set** as the engine rebuild.

### Shared edits (apply to all mixin consumers)
- **Drop `main_sarabun_document_id`** (the per-consumer redundant duplicate). Use the mixin's `active_sarabun_document_id` (current live) / `sarabun_document_ids` (all). The mixin already computes these from `origin_model`/`origin_res_id`.
- In `action_submit_to_sarabun()` (or equivalent), **stop writing the link** (`self.main_sarabun_document_id = document`). The mixin owns the relation. Keep the `action_create_sarabun_document()` call.
- **`state == "sent"` → `active_sarabun_document_id.is_circulating`** (semantic helper).
- **Reject callback signature** `_on_sarabun_rejected(self, document, recipient)` → **`_on_sarabun_rejected(self, document)`**. Re-path the reason/actor: read them from the rejecting **step's** outcome (`actor_id`, `note`/เกษียน, `capacity_position_id`) via `_on_sarabun_step` or a document "last acted step" accessor — **never** `recipient.comment` / `recipient.actioned_by`.
- **Fail-loud / rollback**: audit `button_approved` / `button_rejected` / `action_sign` / `state="approved"` writes — under the new contract a callback failure **rolls back the approver's disposition**. No silent swallow; raise `UserError`/`ValidationError` cleanly.
- **New negative-path callbacks**: implement `_on_sarabun_returned` / `_on_sarabun_cancelled` where the origin must leave its in-flight state (return ⇒ revisable; recall/cancel ⇒ re-openable). Stop stuffing "clear the doc on reject" into the reject callback.
- **XML reports/views**: `o.main_sarabun_document_id.*` → `o.active_sarabun_document_id.*`. The document's free-text `recipient` field is **dropped** → rebind any `.recipient` to the new **เรียน `addressee`** field. Swap `main_sarabun_document_id` view columns/buttons to `active_sarabun_document_id`.
- **Route template data** (`data/sarabun_route_template_data.xml`): templates are now **seed-only**. Re-map line fields to the new step-seed schema (target_mode/position_id, verb, order, for_info).
- **`sarabun.reference`** is dropped — verify no XML data references it (no consumer instantiates it in Python).

---

#### 3.1 `purchase_request_sarabun`
File: `purchase_request_sarabun/models/purchase_request.py` — `purchase.request` inherits `["purchase.request","sarabun.document.mixin","portal.mixin","thai.date.mixin"]`.

- [ ] Delete `main_sarabun_document_id` field declaration.
- [ ] In `action_submit_to_sarabun()` remove `self.main_sarabun_document_id = document`; keep `action_create_sarabun_document()`.
- [ ] `_on_sarabun_rejected(self, document, recipient)` → `_on_sarabun_rejected(self, document)`; read reason from the rejecting step, not `recipient.comment`. Keep `button_rejected()`.
- [ ] Confirm `button_rejected()` / `button_approved()` raise cleanly (rollback semantics).
- [ ] Implement `_on_sarabun_returned` / `_on_sarabun_cancelled` if the PR should revert to draftable/in-progress (returned = revisable; rejected = terminal → duplicate path).
- [ ] XML `reports/report_purchase_request.xml`: `o.main_sarabun_document_id.{name,date,sender_display,subject,recipient}` → `o.active_sarabun_document_id.*`; `.recipient` → `addressee`.
- [ ] XML `views/purchase_request_views.xml`: `main_sarabun_document_id` column → `active_sarabun_document_id`; button visibility already keys on `sarabun_document_count` (survives).
- [ ] `data/sarabun_route_template_data.xml`: re-map to seed-only step template schema.

#### 3.2 `purchase_request_approval` (most-affected)
Inherits the mixin on a second model, declares the **only direct `_inherit "sarabun.document"`**, invents `_on_sarabun_sent`, and is the **only consumer reading `state == "sent"` directly**.

`models/purchase_request_approval.py` — `purchase.request.approval` inherits `[...,"tier.validation","sarabun.document.mixin"]`, `_inherits={"purchase.request":"request_id"}`:
- [ ] **Delete `models/sarabun_document.py` entirely** (the `action_send()` override + `_on_sarabun_sent` push) and remove its import from `models/__init__.py`. The draft→circulating reaction belongs in the engine; re-express via `_on_sarabun_circulating` / `_on_sarabun_step` — **never** re-add an `action_send` monkey-patch.
- [ ] Rename `_on_sarabun_sent(self, document)` → the new circulating hook, keeping the `state="to_approve"` transition.
- [ ] **Fix the canonical guard** in `button_approved()` (≈ line 173): `rec.main_sarabun_document_id.state == "sent"` → `rec.active_sarabun_document_id.is_circulating`; update the message.
- [ ] Delete `main_sarabun_document_id` (≈ line 108–112); use `active_sarabun_document_id`.
- [ ] In `action_submit_to_sarabun()` remove `self.main_sarabun_document_id = document`.
- [ ] `_on_sarabun_rejected(self, document, recipient)` → `_on_sarabun_rejected(self, document)`; reason from step outcome.
- [ ] Ensure `button_approved()` / `button_rejected()` raise safely under rollback (tier.validation interplay — a failing tier check now rolls back the saraban disposition).
- [ ] Add `_on_sarabun_returned` / `_on_sarabun_cancelled` (e.g. back to `validate`/`draft` on return).
- [ ] XML report `report/report_purchase_request_approval.xml` + `views/purchase_request_approval_views.xml`: `main_sarabun_document_id.*` → `active_sarabun_document_id.*`; `.recipient` → `addressee`; swap view column.
- [ ] `data/sarabun_route_template_data.xml`: re-map to seed-only.

#### 3.3 `disbursement_sarabun`
File: `disbursement_sarabun/models/disbursement_request.py` — `disbursement.request` inherits `["disbursement.request","sarabun.document.mixin"]`. Reads `state == "sent"` in a computed gate.

- [ ] Delete `main_sarabun_document_id`; use `active_sarabun_document_id`.
- [ ] Rewrite `_compute_sarabun_in_progress`: depend on `active_sarabun_document_id` and test `is_circulating` instead of `state == "sent"` (or drop the computed field and bind the view to a mixin helper). Fix the `@api.depends` chain to point at `active_sarabun_document_id`.
- [ ] In `action_submit_to_sarabun()` remove `self.main_sarabun_document_id = document`.
- [ ] `_on_sarabun_rejected(self, document, recipient)` → `_on_sarabun_rejected(self, document)`: **remove** `record.main_sarabun_document_id = False` (the 1:N relation is preserved for audit; retry = duplicate-to-draft per ADR-0002). Re-path `recipient.comment` / `recipient.actioned_by.name` to the step outcome.
- [ ] `_on_sarabun_completed` calls `action_sign()` — confirm it raises cleanly (the **financial-integrity** case ADR-0004 cites).
- [ ] Add `_on_sarabun_returned` / `_on_sarabun_cancelled` (return ⇒ stay `submitted`, re-enable submit; recall ⇒ same) — replace the old "clear main doc on reject".
- [ ] XML `views/disbursement_request_views.xml`: `sarabun_in_progress` resolves through the recomputed helper.
- [ ] `data/sarabun_route_template_data.xml`: re-map to seed-only.

#### 3.4 `agx_approval_sarabun`
File: `agx_approval_sarabun/models/approval_request.py` — `approval.request` inherits `["approval.request","sarabun.document.mixin","portal.mixin","thai.date.mixin"]`.

- [ ] Delete `main_sarabun_document_id`; use `active_sarabun_document_id`.
- [ ] In `action_submit_to_sarabun()` remove `self.main_sarabun_document_id = document`.
- [ ] `_on_sarabun_rejected(self, document, recipient)` → `_on_sarabun_rejected(self, document)`; reason from step outcome. **Note**: current code calls `self.action_cancel()` on reject, conflating reject with cancel — split it: map `reject` ⇒ a rejected/cancel state, but handle Sarabun **cancelled/recall** separately via `_on_sarabun_cancelled`.
- [ ] `_on_sarabun_completed` sets `self.state = "approved"` — must raise cleanly under rollback.
- [ ] Add `_on_sarabun_returned` / `_on_sarabun_cancelled` as needed.
- [ ] XML `reports/report_approval_request.xml` + `views/approval_request_views.xml`: `main_sarabun_document_id.*` → `active_sarabun_document_id.*`; `.recipient` → `addressee`; swap tree column.
- [ ] `data/sarabun_route_template_data.xml`: re-map to seed-only.

#### 3.5 `agx_construction` (transitive — follows the PR rename)
Depends on `purchase_request_sarabun`; does **not** inherit the mixin or override callbacks. Only sarabun coupling is a `related` field through `purchase.request`.

File: `agx_construction/models/construction_project.py` — `construction.project`:
- [ ] The `related="purchase_request_ids.main_sarabun_document_id"` field (≈ line 41–45) targets a field being deleted. Replace the path with `purchase_request_ids.active_sarabun_document_id`. Because `purchase_request_ids` is a One2many, a `related` to a single Many2one only resolves the first record — **prefer a computed `active_sarabun_document_id`** (or a One2many `sarabun_document_ids`) that **aggregates across the project's PRs**, rather than a `related`.
- [ ] XML `views/purchase_request_views.xml` (≈ line 76): `main_sarabun_document_id` (on `purchase.request`) → `active_sarabun_document_id`.
- [ ] XML `views/construction_project_views.xml`: update the field reference to the renamed/recomputed field.
- [ ] No callback / `state == "sent"` work needed.

### Cross-module summary
| Concern | Modules | Edit |
|---|---|---|
| Drop `main_sarabun_document_id` → `active_sarabun_document_id` | all 5 (construction via related) | remove field + stop writing; rebind XML |
| `state == "sent"` → `is_circulating` | PR-approval (`button_approved`), disbursement (`_compute_sarabun_in_progress`) | semantic helper |
| Reject callback `(document, recipient)` → `(document)`; reason from **step** | PR-sarabun, PR-approval, disbursement, agx_approval | rewrite `_on_sarabun_rejected` |
| Delete `_on_sarabun_sent` + `action_send` override | **PR-approval only** (`models/sarabun_document.py`) | **delete file**; move to engine hook |
| Add `_on_sarabun_returned` / `_on_sarabun_cancelled` | 4 mixin consumers | implement where negative paths matter |
| Fail-loud / rollback audit | all (esp. disbursement, PR-approval) | no swallow; raise cleanly |
| `recipient` doc field → **เรียน `addressee`** | XML of PR-sarabun, PR-approval, agx_approval | rebind |
| Route templates → seed-only step schema | PR-sarabun, PR-approval, disbursement, agx_approval | re-map data files |
| `sarabun.reference` dropped | none (verify XML) | no action expected |

**Key file paths**
- `purchase_request_sarabun/models/purchase_request.py`
- `purchase_request_approval/models/purchase_request_approval.py` (state=="sent" guard ≈ line 173)
- `purchase_request_approval/models/sarabun_document.py` — **delete** (direct `_inherit "sarabun.document"` + `_on_sarabun_sent`)
- `disbursement_sarabun/models/disbursement_request.py` (state=="sent" in `_compute_sarabun_in_progress`)
- `agx_approval_sarabun/models/approval_request.py`
- `agx_construction/models/construction_project.py` (related on the deleted field)

---

## 4. Risk / rollback note

**Greenfield, not in production → no data migration, no backward-compat.** "Rollback" means reverting the change set, not restoring data.

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Atomicity bug repeats** (old `max()+1` race → duplicate numbers) | High if untested | P3 row-lock + `unique(sequence,number,year)` backstop + retry; explicit concurrent-allocation regression test (§2 P3). The DB constraint is the hard backstop even if the lock logic regresses. |
| **Callback rollback cascade** — a failing origin callback rolls back the approver's disposition, surfacing as an error mid-approval | Medium | Documented as intended (correctness over availability, ADR-0004). Audit each consumer's approve/reject/sign path to raise cleanly (§3). Phase-2 opt-in for "proceed despite failure". |
| **Consumer breakage on cutover** — deleting old models breaks 5 modules | Certain if not co-landed | Migrate all 5 in the **same change set** (§3). CI installs all modules + runs per-consumer integration scenario (§2 P7) before merge. |
| **Access regression** — over-restrict (actors can't see their doc) or under-restrict (waiting steps leak) | Medium | Record-rule tests for both directions (§2 P4), incl. the Position/Unit-no-user_id regression. Manager-see-all stays as a v1 safety valve. |
| **Snapshot vs live confusion** — re-resolving holders rewrites history | Medium | Snapshot written once at activation; immutability test (§2 P2). |
| **Recall after signature** — recall a doc that already has a ลงนาม-อนุมัติ step | Low | `_highest_verb_done()` gate + test; after signature, recall blocked → cancellation หนังสือ. Voided-number gap test ensures the register stays auditable. |
| **Frozen-vs-live PDF** — serving a stale or live file in the wrong state | Medium | Freeze-on-completed + portal serves frozen attachment; pre-completion renders live. State-conditioned controller test (§2 P5). |
| **Phase-2 seam leakage** — acting/secrecy/clerk-gate half-implemented | Medium | Each phase lists explicit seams; v1 stops at the documented line (acting = temp holder; secrecy = label; register = auto-at-send with hook). Seams are hooks/reserved fields, not dead code paths. |

**Rollback procedure:** revert the merge commit. Because nothing is in production there is no data to unwind; the only blast radius is the 5 consumers, which are reverted in the same commit. Land behind a feature branch (`16.0-imp-agx_sarabun-workflow`) and require the full install + integration suite green before merge.

**Recommended landing order:** P1 → P2 → P3 → P4 → P5 as internal commits on the branch (each installable + green), then P6 (adapter + 5 consumers) as the single cutover commit, then P7 hardening. Do **not** merge to `16.0` until P6 lands, since the old models can only be deleted once consumers are migrated.
