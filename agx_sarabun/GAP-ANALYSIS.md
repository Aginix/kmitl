# GAP-ANALYSIS — agx_sarabun (old module)

A code-grounded inventory of the bugs, blind spots and design gaps in the **old** `agx_sarabun` module that motivate the rebuild. Each finding cites file:line or symbol as evidence, states why it is wrong, and how the new design (CONTEXT term / ADR) resolves it.

Scope of code reviewed: `models/`, `wizard/`, `controllers/`, `security/`, `report/`, `data/`, `documentation.md`. Line references are against the source as read on the rebuild branch.

---

## Critical

### C1. No `rejected` state — rejection is a permanent dead-end
- **Evidence:** `models/sarabun_document.py:188-201` (`state` selection = `draft / sent / completed / cancelled`, no `rejected`); `_check_completion()` at `models/sarabun_document.py:753-757` explicitly `return`s and leaves the document in `sent` when a recipient is rejected.
- **Why it's wrong:** A rejected document is stuck in `sent` forever — it never reaches a terminal state, the chain cannot advance, and there is no path to revise or supersede it. The origin is told via callback but the หนังสือ itself lies dead.
- **How the new design resolves it:** ADR-0002 defines `rejected` as a real terminal state; ปฏิเสธ (Reject) is a first-class disposition (CONTEXT *Dispositions*), and "to proceed you duplicate to a new draft" (origin↔document is 1:N, ADR-0004).

### C2. Forward & reject wizards call methods that do not exist on the target model
- **Evidence:** `wizard/sarabun_routing_wizard.py:26` calls `self.routing_line_id.action_do_reject(...)` and `:68` calls `self.routing_line_id.action_do_forward(...)`. Grep confirms `action_do_reject`/`action_do_approve`/`action_do_acknowledge` exist only on `sarabun.document.recipient` (`models/sarabun_document_recipient.py:204,237,289`) — and `action_do_forward` **exists nowhere in the module**.
- **Why it's wrong:** `SarabunRoutingRejectWizard.action_reject` and `SarabunRoutingForwardWizard.action_forward` would raise `AttributeError` the instant they run — they target `sarabun.routing.line`, the plan table, which has no action methods. There is no forwarding capability at all.
- **How the new design resolves it:** The Route is a single mutable `sarabun.routing.step` entity (ADR-0001); dispositions (เกษียนสั่งการ Direct, มอบหมาย Delegate, ตีกลับ Return, ปฏิเสธ Reject) are first-class operations on the live step, so there is no plan/tracker split to mis-target.

### C3. Document number race + wrong fiscal reset
- **Evidence:** Next-number is `max(used_numbers) + 1` computed in Python: `models/sarabun_document_sequence.py:118-119` (`_compute_next_number`), consumed by `get_next_number()` → `get_next_and_use()` (`:248-253`) called from `_generate_document_number()` (`:700`). No row-lock / `SELECT ... FOR UPDATE`. Reset: `_check_year_reset()` (`:136-141`) only handles `reset_period == "yearly"` and uses `fields.Date.today().year` (calendar year) — the `"fiscal_year"` option (`:46`) is never acted on.
- **Why it's wrong:** Two concurrent sends read the same `max()` and both allocate the same number — a classic TOCTOU race the regulation forbids. And the advertised fiscal-year reset silently never fires, so numbers roll over on 1 Jan instead of 1 Oct.
- **How the new design resolves it:** CONTEXT *ลงทะเบียน (Register)* — allocate atomically (row-lock + `unique(sequence,number,year)` backstop + retry), reset per ปีงบประมาณ (Oct–Sep) by default, render in พ.ศ.

### C4. Record rule hides documents from Position/Unit recipients (the `recipient_ids.user_id` bug)
- **Evidence:** `security/security.xml:47` — `sarabun_document_recipient_rule` domain `[('recipient_ids.user_id', '=', user.id)]`. But department/role recipients carry no `user_id` (`models/sarabun_document_recipient.py:56-70`); access is decided by `sarabun_officer_ids` / role users at runtime (`_can_user_access`, `:440-458`). Same flaw in the routing-line and recipient rules (`security.xml:91-93,103-106`) and the activity view domain (`views/sarabun_document_views.xml:390`).
- **Why it's wrong:** A user who must act on a `department`- or `role`-type recipient cannot even *read* the document — the ir.rule filters it out because there's no `user_id` on that recipient row. The feature is broken for everyone except direct user-targets.
- **How the new design resolves it:** CONTEXT *Route visibility* (explicitly: "FIX the old `recipient_ids.user_id` rule that hid documents from Position/Unit actors") — readable by sender + the snapshot actors of any active/completed step, where Position/Unit holders are resolved and snapshotted onto the step.

### C5. `read()` override writes to the DB inside a read (anti-pattern)
- **Evidence:** `models/sarabun_document.py:780-791` overrides `read()` and calls `record.sudo()._mark_recipient_read()` when `fields is None or "subject" in fields`; mirrored in `models/sarabun_document_recipient.py:428-438` which calls `mark_as_read()` (writes `read_date`).
- **Why it's wrong:** Mutating the database from `read()` is a correctness and performance hazard — it fires on every list/kanban/export, depends on a brittle "is `subject` in the requested fields" heuristic to guess "is this a form view", and runs writes (and `sudo()` writes) on a read path.
- **How the new design resolves it:** Remove the read()-override anti-pattern entirely (RESOLVED ARCHITECTURE — Notifications). Use native `mail.activity` for "action required" plus a lightweight sarabun inbox/systray + bus realtime; read-tracking is not done inside `read()`.

### C6. Origin callbacks silently swallow exceptions (financial data-integrity hole)
- **Evidence:** `_on_routing_completed` (`models/sarabun_document.py:800-815`), `_on_routing_rejected` (`:826-840`), `_trigger_origin_action_callback` (`:842-858`) each wrap the origin call in `try/except Exception` + `_logger.exception(...)` and continue.
- **Why it's wrong:** If a PR→budget or disbursement callback fails, the saraban document still completes — leaving "approved in saraban but not in the origin", exactly the integrity disaster ADR-0004 warns about. The swallow is silent to the approver.
- **How the new design resolves it:** ADR-0004 — callbacks run in the **same transaction** as the actor's action and a failing origin callback **rolls the action back** (no silent swallow); correctness over availability.

### C7. Routing is strictly sequential — no parallel stages, no CC
- **Evidence:** `_activate_next_recipient()` (`models/sarabun_document.py:711-744`) creates exactly **one** recipient — the next line by `sequence` not yet materialised — and `_check_completion` advances only when the prior is done. Acknowledge/approve both end by calling `_activate_next_recipient()` (`recipient.py:235,271`).
- **Why it's wrong:** Co-approval, parallel รับทราบ, and สำเนาเรียน (CC) are impossible — every recipient must finish before the next is even created. Real correspondence routinely fans out.
- **How the new design resolves it:** CONTEXT *Stage* — steps sharing one `order` run in parallel; advance when all *gating* steps complete; รับทราบ never blocks; สำเนาเรียน is a non-gating step flagged `for_info` (ADR-0001).

### C8. Sign-as-any-role — no validation against the step's target Position
- **Evidence:** `models/sarabun_role.py:127-134` `get_user_roles()` returns **every** role the user holds; the signing wizard offers all of them (`wizard/sarabun_signing_wizard.py:62-65`) and `action_do_approve`/`action_do_acknowledge` write whatever role was picked (`recipient.py:209-217,245-253`) with no check that it matches the recipient's `role_id`.
- **Why it's wrong:** A user can sign/approve in *any* capacity they happen to hold, not the capacity the step actually targets — e.g. approve a คณบดี step while signing as a different role. The signed-as capacity is unconstrained.
- **How the new design resolves it:** ADR-0003 — signing capacity is validated against the step's **target Position** (or an acting capacity of it), not any role the user holds.

---

## Major

### M9. Recipient "soup" — `recipient` / `recipient_ids` / `sarabun.document.recipient` are three different things
- **Evidence:** (a) free-text header field `recipient` "To" (`models/sarabun_document.py:154-159`); (b) tracking O2m `recipient_ids` → `sarabun.document.recipient` (`:217-223`); (c) the tracker model itself. Plus `recipient_type` on lines/recipients with values `user/department/role` (`routing_line.py:44-53`).
- **Why it's wrong:** One word means the printed addressee, the delivery-tracker collection, and the per-actor row — confusing in code and UI, and the addressee floats free of who actually acts.
- **How the new design resolves it:** CONTEXT splits these cleanly: เรียน *Addressee* is its own header field (optionally with ผ่าน), routing actors live on `sarabun.routing.step`, and *Targeting mode* replaces the `user/department/role` vocabulary with Position/Person/Unit.

### M10. Two-table line/recipient model that must be kept in sync
- **Evidence:** `sarabun.routing.line` is the plan (docstring `routing_line.py:11-15`: "no state tracking"); `sarabun.document.recipient` is the tracker; fields are hand-copied at activation (`sarabun_document.py:729-740`) and the line back-computes status from its recipient (`routing_line.py:112-119`).
- **Why it's wrong:** Two tables holding half a step each must be synchronised; mid-flow insertion is awkward, and `recipient.routing_line_id` is `ondelete="set null"` (`recipient.py:25-30`) so deleting a line orphans its tracker. Drift is structural.
- **How the new design resolves it:** ADR-0001 — one `sarabun.routing.step` entity (target + verb + state + outcome) replaces the line/recipient split; "nothing to keep in sync and steps can be inserted mid-flow".

### M11. "All approval steps must be at the end" band-aid constraint
- **Evidence:** `action_send` (`models/sarabun_document.py:488-500`) raises `ValidationError` if any `approve` line has `sequence < max(sequence)`. Reinforced by `ROUTING_TYPE_SEQUENCE = {"acknowledge": 10, "approve": 100}` auto-sequencing (`routing_line.py:5-8,98-109`).
- **Why it's wrong:** It bans legitimate flows (approve → then a รับทราบ CC; endorse mid-chain then sign) — a symptom of the sequential-only engine, not a real records rule.
- **How the new design resolves it:** ADR-0001 explicitly calls this the "approval-must-be-last band-aid"; the dynamic stage engine with gating/non-gating verbs (เห็นชอบ mid-chain, รับทราบ at the end) makes the constraint unnecessary.

### M12. Cancellation blocked entirely after send — no Recall, no cancellation-after-signature path
- **Evidence:** `action_cancel` (`models/sarabun_document.py:516-526`) raises "Once sent, documents cannot be cancelled" for any non-draft state; documentation.md:282 confirms "ยกเลิกในขั้นตอน draft เท่านั้น".
- **Why it's wrong:** There is no เรียกคืน (recall a circulating doc before signing) and no concept that a signed doc must be voided via a cancellation หนังสือ — the only cancel is on a draft, which is just a delete.
- **How the new design resolves it:** ADR-0002 — `cancelled` via เรียกคืน (Recall) permitted **only before any ลงนาม-อนุมัติ step has occurred**; after a signature, a cancellation หนังสือ is required. The engine tracks the strongest verb completed so far.

### M13. Live report render after "completion" — no frozen ฉบับลงนาม
- **Evidence:** Portal always renders live: `controllers/portal.py:91-105` and `:135-162` re-render the QWeb report (or delegate to the **live** origin report) on every request, including completed docs. documentation.md:408-413 advertises "Real-time data … No file attachment" as a *benefit*.
- **Why it's wrong:** A completed/signed official document must be immutable; rendering it live means the origin record changing later silently changes the "signed" output — the record is not fixed.
- **How the new design resolves it:** CONTEXT *ฉบับลงนาม (Signed copy)* — freeze an immutable PDF at `completed`; portal/print serve the frozen file thereafter, live preview only before completion.

### M14. Secrecy / ชั้นความลับ is captured but never enforced
- **Evidence:** `secrecy` Selection field (`models/sarabun_document.py:108-119`) but no ir.rule, domain or access check references it anywhere (`security/security.xml` rules are sender/recipient/manager only).
- **Why it's wrong:** "Secret / Top Secret" is a label with zero need-to-know effect — a misleading promise of confidentiality.
- **How the new design resolves it:** CONTEXT *Route visibility* — v1 treats secrecy as a display label explicitly (manager-see-all stays), with ชั้นความลับ need-to-know enforcement scoped as phase-2, so the gap is an acknowledged seam rather than a silent false promise.

### M15. Hardcoded `document_type.code` Selection conflates behaviour-key and identifier
- **Evidence:** `models/sarabun_document_type.py:15-23` — `code` is a `Selection(memo/circular/from_record)`; `sarabun_document.py:72-75` mirrors it as a stored related `document_type_code`. The integration docs even search `[("code", "=", "internal")]` (documentation.md:47) — a value not in the selection, so that example is already broken.
- **Why it's wrong:** A single hardcoded selection doubles as both the dev-level behaviour key and the admin-facing type identifier; admins cannot add a new concrete type without code changes, and the two concerns are tangled.
- **How the new design resolves it:** CONTEXT *Document kind* vs *Document type* — a fixed dev-extensible `kind` (memo/circular/from_record) split from admin-configurable `sarabun.document.type` records that bind sequence/route/template and point at one kind.

### M16. `sarabun.reference` is a hardcoded ERP-record picker, not อ้างถึง
- **Evidence:** `models/sarabun_reference.py:19-30` — `res_model` is a fixed `Selection` of purchase.request / purchase.order / budget.commitment / budget.move / account.move.request / account.move.
- **Why it's wrong:** This conflates "related ERP records" with the regulation's อ้างถึง (links to prior หนังสือ + free-text external letters); the model list is hardcoded and redundant with the origin link.
- **How the new design resolves it:** CONTEXT *อ้างถึง (Reference)* explicitly drops `sarabun.reference` ("that was related ERP records, not อ้างถึง"); references become m2m prior `sarabun.document` + free-text lines, distinct from the origin link.

### M17. Dynamic roles resolve live, with no snapshot of who actually acted
- **Evidence:** `sarabun.role.get_users_for_document()` (`models/sarabun_role.py:92-116`) recomputes sender_manager / dept_head / parent_dept_head **on every access/action call** (`recipient._can_user_access`, `_check_can_action`, `_send_notification`). No snapshot of the resolved person-set is stored on the recipient.
- **Why it's wrong:** If the org chart changes mid-flow (manager reassigned), who may act and who is shown as the actor shifts under the document — history can be rewritten and the authorised actor set is non-deterministic.
- **How the new design resolves it:** ADR-0003 — a Position resolves to its current holder(s) **at the moment the step becomes active** and that person-set is **snapshotted** onto the step, so later org changes never rewrite history.

### M18. No incoming / external side — system is outgoing-only
- **Evidence:** `sender_*` fields and a `recipient` "To" string exist (`sarabun_document.py:121-159`) but there is no inbound register, no Unit (สารบรรณกลาง) targeting that receives external letters; `recipient_type` "department" routes to `sarabun_officer_ids` for *internal* notification only (`recipient.py:362-369`).
- **Why it's wrong:** e-Saraban must handle incoming correspondence (หนังสือรับ) routed through a department's central registry; the old module only models documents *originating* from a sender.
- **How the new design resolves it:** CONTEXT *Targeting mode* — **Unit** (a department's สารบรรณกลาง / central registry, "used mainly for incoming หนังสือ") is a first-class targeting mode resolving to holders and snapshotting onto the step.

### M19. No tests at all
- **Evidence:** No `tests/` directory in the module (file inventory confirms); `__manifest__.py` lists no test deps and the project CLAUDE.md test conventions are unused here.
- **Why it's wrong:** A workflow engine with numbering, state transitions, callbacks and access rules ships with zero automated coverage — every one of the bugs above is untested.
- **How the new design resolves it:** Greenfield rebuild (RESOLVED ARCHITECTURE: "NOT in production → greenfield") with the project's documented mixin/transition test patterns applied to the new step engine, lifecycle and atomic numbering.

### M20. Per-consumer `main_sarabun_document_id` / weak 1:N origin link
- **Evidence:** The mixin exposes only a computed `sarabun_document_ids` + count (`models/sarabun_document_mixin.py:25-45`) and no `active_sarabun_document_id`; ADR-0004 documents that each of the 5 consumers re-declares its own `main_sarabun_document_id` and hardcodes `state == "sent"` checks. Callbacks pass a `recipient` (`mixin.py:119-147`), not a step.
- **Why it's wrong:** No canonical "current live document" pointer; consumers diverge with their own m2o; the reject→duplicate (1:N) case has no first-class representation; callbacks leak the soon-to-be-removed recipient entity.
- **How the new design resolves it:** ADR-0004 — the mixin **owns** the relation and exposes `sarabun_document_ids` + `active_sarabun_document_id`, callbacks (`_on_sarabun_completed/_rejected/_returned/_cancelled` + generic `_on_sarabun_step(step, disposition)`) pass a `sarabun.routing.step`, and semantic helpers (e.g. `is_circulating`) replace `state == "sent"`.

### M21. `sarabun.role.role_category` wrongly merges Position with academic rank
- **Evidence:** `models/sarabun_role.py:33-42` — one model carries `role_category = executive | academic` ("Executive: คณบดี… Academic: ศาสตราจารย์…").
- **Why it's wrong:** It treats an administrative authority position and a scholarly title as variants of one "role" — but academic rank is display-only and never a routing target or signing authority.
- **How the new design resolves it:** ADR-0003 / CONTEXT *Academic rank* — `sarabun.position` is the routing/signing catalog; academic rank lives on the person (`hr.employee.academic_standing_title`) and renders only in the signature block.

---

## Minor

### m22. `completed_count >= all_lines_count` completion check is fragile
- **Evidence:** `_check_completion` (`models/sarabun_document.py:759-768`) compares count of acknowledged/approved recipients against `len(routing_line_ids)`.
- **Why it's wrong:** Couples completion to two separate tables' cardinalities (the very line/recipient split of M10); inserting/removing a line mid-flow desynchronises the count, and rejected/never-materialised lines confound it.
- **How the new design resolves it:** CONTEXT *Stage* / *first-to-act* — completion is evaluated per-stage over gating steps on the single step entity, not by counting two tables.

### m23. Sequence `format_number` renders no year / no พ.ศ. and gaps are deletable
- **Evidence:** `format_number` (`models/sarabun_document_sequence.py:234-246`) emits only prefix+padded number+suffix — no year segment; `action_release` (`:377-387`) **unlinks** a used number, and `action_cancel_reservation` flips reserved→cancelled with no voided-gap semantics on the document side.
- **Why it's wrong:** Official numbers should embed the (Buddhist) year and a cancelled/rejected number must remain a permanent recorded gap; deleting the number row erases the audit gap.
- **How the new design resolves it:** CONTEXT *Voided number (เลขยกเลิก)* + *Register* — render in พ.ศ., never recycle, keep the gap as a recorded ยกเลิก.

### m24. Cover sheet / signature block / เกษียน trail not rendered on the document
- **Evidence:** `report/report_sarabun.xml:3-87` prints header + raw `content` + an empty signature dotted-line (`:75-82`); no actor/เกษียน trail, no academic prefix, no digitized signature, no merge with origin body. Grep shows `academic_standing_title`/`digitized_signature` referenced only in CONTEXT.md, never in code.
- **Why it's wrong:** The endorsement/signing history and the real signature block are invisible on the official output; for `from_record` the origin body is delegated as a *separate* live render, never merged.
- **How the new design resolves it:** CONTEXT *Signature block*, *เกษียน trail*, *ใบปะหน้าสารบรรณ* — a system-rendered cover sheet (header + signature block + เกษียน trail) merged with the origin report into one frozen PDF.

### m25. Inbox/systray & access keyed on the literal string `state == "sent"`
- **Evidence:** `models/res_users.py:19` filters inbox by `("document_id.state", "=", "sent")`; recipient guard `recipient.py:329`; numerous view decorations (`views/sarabun_document_views.xml:8,73,317,…`).
- **Why it's wrong:** The lifecycle state is renamed `circulating` in the new model; every hardcoded `"sent"` is a brittle literal that breaks on rename and bypasses semantic intent.
- **How the new design resolves it:** CONTEXT *Circulating* + ADR-0004 semantic helpers (e.g. `is_circulating`) replace hardcoded `state == "sent"` checks throughout.

### m26. Notification only reaches a department's officers/manager, never plain members; dynamic-role notify can silently reach nobody
- **Evidence:** `_send_notification` (`models/sarabun_document_recipient.py:352-403`) notifies `sarabun_officer_ids`, else `manager_id.user_id`; for roles it notifies `get_users_for_document`, which can return an empty recordset (e.g. dept head with no `user_id`, `sarabun_role.py:107-116`) — then no activity, no inbox, no bus message is created and the chain stalls with no actor.
- **Why it's wrong:** A step can become "active" with zero notifiable actors and no error — the document silently hangs.
- **How the new design resolves it:** RESOLVED ARCHITECTURE (Notifications + Numbering "block with a clear error" philosophy) — Position/Unit resolve to a concrete snapshot holder-set; multi-holder steps notify **all** holders via `mail.activity` and auto-clear siblings on first-to-act; an unresolvable target is surfaced, not swallowed.
