# e-Saraban (สารบรรณอิเล็กทรอนิกส์)

Electronic official-correspondence (งานสารบรรณ) for KMITL. The **หนังสือ (Document) is the protagonist**: it is registered, numbered per the records regulation, and routed through an approval/endorsement chain. A heavy emphasis sits on the **approval-routing engine** — how a document flows through people/positions for เกษียน → เสนอ → ลงนาม → รับทราบ. Integration with other modules (e.g. a purchase request that spawns a memo) is a *secondary adapter*, not the centre of gravity.

## Language

**Document (หนังสือ / เอกสาร, `sarabun.document`)**:
The protagonist — one official correspondence item that is registered, numbered, and routed. Everything else (route, steps, register entries) hangs off it.
_Avoid_: ticket, request, approval (those describe the routing, not the หนังสือ)

**Origin record**:
A business object in another module (e.g. `purchase.request`) that spawns a Document and is notified of its outcome via callbacks. It is the *adapter* side, never the protagonist — the engine must not bend toward approval semantics to serve it. One origin may own **several** Documents over time (a rejected one is superseded by a duplicated new draft — see ADR-0002), so the relation is 1:N; the mixin exposes all of them plus an `active_sarabun_document_id` pointer to the current live one. The mixin also **reflects the active Document's status back onto the origin** (draft-not-sent / routing progress / state) so the source form shows where its หนังสือ stands.
_Avoid_: source document, parent (reserve "document" for the หนังสือ itself); a 1:1 origin↔document assumption

**Route**:
The **living, ordered chain of steps that lives on the Document** and flows through people/positions. It is mutable at runtime — authorised actors may insert, append, redirect, return, or CC mid-flow (เกษียนสั่งการ). The Route is not a frozen copy of a template; it *is* the document's current state of who-acts-next.
_Avoid_: workflow, approval flow (those imply a fixed pre-planned graph)

**Route Template**:
A reusable preset that *seeds* a Route's steps at send time (e.g. a standard PR-approval chain). It is a convenience pre-fill only — it does **not** own or constrain the flow once seeded.
_Avoid_: workflow definition, process (it is not the source of truth for the flow)

**Routing Step (`sarabun.routing.step`)**:
One row of a Route = *target* (who acts) + *verb* (what they must do) + *state* + *outcome* (who acted, when, the เกษียน note, the capacity they signed in). A **single entity** — it replaces the old `routing.line` (plan) / `document.recipient` (tracker) split, so there is nothing to keep in sync and steps can be inserted mid-flow.
_Avoid_: routing line, recipient (both meant half of a step in the old model)

**เกษียนสั่งการ (Direct)**:
A first-class action by the actor at a step: annotate, then insert/redirect the next step(s) at runtime. Treated as the *common* path of routing, not an exception.
_Avoid_: forward (forward implies handing off without annotation/authority)

**Position (ตำแหน่งบริหาร, `sarabun.position`)**:
An administrative/authority position — the **primary routing target** and the capacity a document is signed in (คณบดี, ผอ.กอง, อธิการบดี). Purpose-built for e-Saraban, distinct from `hr.job` (employment position) and from academic rank. Its **holder(s) are personnel (`hr.employee`)**; when a step becomes *active* the engine resolves each holder to their **linked user account** and **snapshots** that user-set onto the step, so later org changes never rewrite history. A holder without a linked user may be listed but can never act (see ADR-0005). (รักษาการ/มอบอำนาจ — acting & delegated authority — is a planned phase-2 seam; interim, add the acting person as a temporary holder.)
_Avoid_: role, hr.job, job position; res.users as the holder (holders are personnel, resolved to a user only to act)

**Academic rank (วุฒิ/คำนำหน้าทางวิชาการ)**:
A person's scholarly title (ศ., รศ., ผศ., ดร.) shown in the signature block **for display only** — never a routing target or signing authority. The old `role_category` wrongly merged this with Position.
_Avoid_: position, role

**Targeting mode**:
What a Routing Step points at — exactly one of **ตำแหน่ง (Position)** (canonical), **บุคลากร (Person)** (a specific `hr.employee`), or **ธุรการหน่วยงาน (Unit clerk)** (the document clerk(s) configured on a หน่วยงาน, `hr.department`). All three are configured as personnel (`hr.employee`) and resolved to a user account to act (see Position / ADR-0005).
_Avoid_: the old `recipient_type` vocabulary "user / department / role"; framing the unit target as a "central registry" or single institute-wide office (it is the per-หน่วยงาน clerk)

### Step verbs (what a step requires)

Step verbs are **admin-configurable master data** (`sarabun.verb`); the built-ins below are seeded and referenced by the engine via their **xmlid** (`agx_sarabun.verb_*`) — there is no separate identity/code field. Admins may add or relabel verbs. A verb carries **three independent axes** (ADR-0008): **`gating`** (must be positively completed for its Stage to pass), **`show_signature`** (renders a signature block on the official document — the แสดง / ไม่แสดงลายเซ็น toggle), and **`is_signature`** (an authoritative approval-sign that closes the ดึงกลับ / ยกเลิก window and signs in the step's Position capacity). Invariant: `is_signature ⇒ show_signature`. Two verbs may share the same three axes and still be kept as **distinct records** — the label is the human instruction the actor reads ("what am I being asked to do"), so a different instruction earns its own verb even when behaviour coincides. The catalogue below is the **UAT-reviewed set** (the earlier behaviour-derived 6 were replaced on UAT feedback); it is **provisional, pending review after real use**. The ผู้จัดทำ verbs are separate (see originator) and were left untouched by the UAT revision.

**รับทราบ / ถือปฏิบัติ / จัดเก็บเข้าแฟ้ม (Acknowledge, read-only)** — gating ✗ · show_signature ✗:
For information; the actor confirms receipt. **Non-gating** — does not block the chain and may run in parallel; renders nothing on the letter.

**รับทราบและลงนาม (Acknowledge & sign)** — gating ✗ · show_signature ✓:
An acknowledgement that also **puts a signature on the letter** (e.g. a post-decision sign-off). Still **non-gating** — never blocks the chain.

**ตรวจเอกสาร (Check)** — gating ✓ · show_signature ✗:
An intermediate actor must check the document before it moves on, but **carries no signature** — name in the Route, not on the letter.

**ผ่านเรื่อง / กลั่นกรอง (Screen)** — gating ✓ · show_signature ✓:
A screening gate the matter must pass; the screener **signs** (ลงนามกำกับ). **Gating**; not the authoritative sign.

**ตรวจสอบและลงนามกำกับ (Verify & countersign)** — gating ✓ · show_signature ✓:
Verify and **countersign**. **Gating**; not the authoritative sign (does not close recall).

**พิจารณา / ให้ความเห็นและลงนามกำกับ (Consider & countersign)** — gating ✓ · show_signature ✓:
Give an opinion and **countersign**, passing upward. **Gating**; may also ตีกลับ / ปฏิเสธ. Not the authoritative sign (does not close recall).

**ลงนามในใบปะหน้า / เอกสารเพื่อลงนาม (Sign-out)** — gating ✓ · show_signature ✓ · is_signature ✓:
The authoritative signature that **issues** the หนังสือ (ส่งออก), made in the capacity of the step's target Position. **Gating**, and closes the recall window.

**อนุมัติ / อนุญาต / เห็นชอบและลงนามกำกับ (Approve & sign)** — gating ✓ · show_signature ✓ · is_signature ✓:
An approving authority's **decision and signature**. Also **authoritative** — closes the recall window (a document may legitimately have more than one authoritative sign; the *first* to occur closes ดึงกลับ / ยกเลิก).
_Avoid_: coupling "shows a signature" with "gating" (they are independent axes — ADR-0008); assuming a **single** authoritative signer (both Sign-out and Approve are is_signature — supersedes the earlier "only ลงนาม-อนุมัติ" wording in ADR-0008); a pure non-signing "ส่งต่อ (Forward)" verb (dropped in the UAT set — a pass-along now either checks, screens, or acknowledges)

### Dispositions (how the active actor responds)

The set of moves available at an active step, subject to authority: **complete** (perform the required verb) · **เกษียนสั่งการ (Direct)** (I acted, now insert the next step) · **มอบหมาย (Delegate)** (I will not act — X performs *this* step instead) · **ตีกลับ (Return)** (send back for revision) · **ปฏิเสธ (Reject)** (terminal negative). **ตีกลับ and ปฏิเสธ are available only on a *gating* step (เห็นชอบ / ลงนาม-อนุมัติ) and only to that step's own active actor** — a รับทราบ / สำเนาเรียน (CC) recipient may only complete (acknowledge), and the sender/manager cannot ตีกลับ/ปฏิเสธ on an actor's behalf (contrast ดึงกลับ / ยกเลิกการส่ง, which *are* the sender's).
_Avoid_: treating มอบหมาย and เกษียนสั่งการ as the same move — Delegate reassigns *this* step, Direct inserts the *next*; letting a CC/รับทราบ actor ตีกลับ.

### Lifecycle

**Circulating (กำลังดำเนินการ)**:
A Document in flight along its Route. Renamed from the old `sent` to capture "moving through the chain", not "delivered once".
_Avoid_: sent, in transit

**ตีกลับ (Return)**:
Send a circulating Document back for revision — available **only to the active actor of a gating step** (see Dispositions). The returner **picks the destination every time**: the **previous stage** (resume — the default), the **original sender** (restart the chain), or **any earlier step** to resume from. Lands the Document in state `returned` (revisable like a draft; the prior chain is **archived as history, never overwritten**). A **reason is required** and kept in the routing history.
_Avoid_: reject (Return is recoverable; Reject is terminal); a fixed sender-restart default (the returner chooses each time)

**ดึงกลับ (Recall)**:
The **sender** pulls a circulating Document **back to an editable state**, to revise and re-send (แบบ pull-back-to-edit). The prior routing chain is archived as history and the chain restarts on re-send; the Document lands in state `returned` — behaving as a self-initiated ตีกลับ-to-sender. Permitted **only while no ลงนาม-อนุมัติ step has occurred**. Contrast ยกเลิกการส่ง: ดึงกลับ is recoverable and expects a re-send; ยกเลิกการส่ง is terminal. (Since ADR-0010 the number runs only at completion, so neither act touches a number — a circulating หนังสือ has none.)
_Avoid_: เรียกคืน (one term now — ดึงกลับ); "keeps the number" as the distinguishing trait (there is no number yet — ADR-0010; the distinction is recoverable-vs-terminal)

**ยกเลิกการส่ง (Cancel-send)**:
The **sender** withdraws a circulating Document **terminally** — it lands in state `cancelled`. For "this send should never have happened", not "let me fix it" (that is ดึงกลับ). Permitted **only while no ลงนาม-อนุมัติ step has occurred**; once a signature exists the Document is part of the record and withdrawal instead requires issuing a cancellation หนังสือ. (Since ADR-0010 the หนังสือ was never numbered at this point, so there is no number to void.)
_Avoid_: ดึงกลับ (ดึงกลับ is recoverable and re-sends; ยกเลิกการส่ง ends the Document); recall / เรียกคืน (the old name conflated these two acts); "voids the number" (nothing to void — ADR-0010)

**Voided number (เลขยกเลิก)**:
A register ledger row marked as a permanent, never-reissued gap. **Largely historical since [ADR-0010](./docs/adr/0010-register-number-at-completion-not-at-send.md):** because a number is now issued only at completion, rejected/cancelled documents were never numbered and so produce no voided gaps on the normal path — the mechanism (`_void_register`, `state='voided'`) is retained only for the reserved/manual compose paths. Where such a voided row *does* exist, an admin **Reset** ([ADR-0011](./docs/adr/0011-admin-reset-to-draft.md)) may let the *original* Document **reclaim its own** number (un-void → `used`), audited on the ledger + chatter; a voided number is still never handed to a *different* Document.
_Avoid_: released number, reusable number; treating voided gaps as a normal outcome of reject/cancel (they no longer are — ADR-0010); reissuing a voided number to *another* Document (only the original may reclaim its own, via Reset — ADR-0011)

**Reset (to draft — admin override, ADR-0011)**:
An **admin-only** force-return of a หนังสือ from **any non-draft state** — including `completed`, and even the otherwise-terminal `rejected` / `cancelled` — back to an editable **`draft`**, **keeping its registered number (when it has one) and its original Route**. It exists for the case ดึงกลับ cannot serve: a mistake found *after* the document is signed / completed (typically a typo in an already-fully-approved หนังสือ) that must be corrected and re-sent from the start. It **archives the finished attempt as history** (never overwrites — prior signatures survive on the archived Route), **recreates the Route as it was originally created** (the seeded backbone; runtime เกษียนสั่งการ insertions are *dropped*), **un-freezes** the ฉบับลงนาม (the prior signed PDF is discarded), and **rolls the origin back** so it is treated exactly like a ดึงกลับ. Since [ADR-0010](./docs/adr/0010-register-number-at-completion-not-at-send.md) only a `completed` หนังสือ carries a number, so "keep the number" bites in the completed case — its number survives the reset and is re-used verbatim when it re-completes (`_assign_register_number` is idempotent); resetting an unnumbered `circulating` / `returned` / `rejected` / `cancelled` หนังสือ simply has no number to keep (any rare voided reserved/manual number is reclaimed). A reason is mandatory (kept in chatter). It is a **deliberately separate, optional capability** — not every deployment grants it.
_Avoid_: equating Reset with ดึงกลับ (Reset is admin-only, works *after* signing / completion / rejection, and un-freezes); treating `rejected` / `cancelled` as absolutely terminal (Reset is the one admin escape); carrying the prior run's เกษียนสั่งการ insertions into the new Route (Reset restores the original); assuming every reset หนังสือ has a number to keep (only a completed one does — ADR-0010)

### Concurrency

**Stage**:
The set of Routing Steps sharing one `order` — they run **in parallel**. The Route advances to the next Stage when every *gating* step (เห็นชอบ / ลงนาม-อนุมัติ) in the current Stage is positively completed. Sequential routing is just stages of one step each.
_Avoid_: level, round

**สำเนาเรียน (CC / for-info)**:
A non-gating รับทราบ step — often parallel and at the final stage. Modelled as an ordinary step flagged `for_info`, **not** a separate entity. Pending CCs never block completion; they are only tracked ("ค้างรับทราบ N").
_Avoid_: a separate copy/recipient list

**First-to-act (quorum)**:
When a step targets a Position or ธุรการหน่วยงาน held by several people, the **first holder to act completes it** on the group's behalf. "Everyone must act" is expressed as several parallel steps instead, never as a quorum rule on one step. A single ปฏิเสธ within a co-approval Stage rejects the whole Document immediately.
_Avoid_: all-must-approve quorum on a single step

### Numbering

**ลงทะเบียน (Register)**:
The act of assigning a Document its official running number from a sequence. It fires **automatically at completion** — when the **final** ผู้มีอำนาจลงนาม/อนุมัติ has signed ([ADR-0010](./docs/adr/0010-register-number-at-completion-not-at-send.md)), so a หนังสือ has **no number while it travels its approval route** (ที่ = `/` throughout `draft`/`circulating`/`returned`) — but is kept a *distinct event* so a ธุรการหน่วยงาน clerk-gate can be inserted in phase 2. **Send** does not number; it only *verifies* a register resolves (fail-fast). The sequence is resolved automatically from the **sender ส่วนงาน** — each ส่วนงาน issues from **one register shared across all its document types** (a หน่วยงาน keeps a single running number series; the earlier per-`(ส่วนงาน × type)` split was dropped on feedback), not one institute-wide pool; if no sequence is configured for that unit the send is **blocked with a clear error**, never silently numbered from a default. Numbers reset per **ปีงบประมาณ (fiscal year, Oct–Sep)** by default and render in พ.ศ.; the number's ปีงบ is taken from the **completion (registration) moment**. A number is allocated atomically (row-locked) and never recycled. Because it is issued only on successful completion, an abandoned (rejected/cancelled) หนังสือ consumes **no** number — the series has no gaps from failed routes. While unnumbered (throughout `draft`/`circulating`/`returned`) the หนังสือ is referred to **by its เรื่อง** — there is **no interim/temporary reference code**; the official number replaces the เรื่อง as its identifier only once ลงทะเบียน runs. **Operationally a หนังสือ never straddles a ปีงบประมาณ boundary** — a draft prepared near year-end is only *ส่ง* in the new year — so the completion ปีงบ (which the number uses) and the ลงวันที่ ปีงบ always coincide.
_Avoid_: numbering (reserve "register" for the official, audited act); assuming a circulating หนังสือ already has its number (it does not — ADR-0010); an interim/provisional number during the route (there is none — the เรื่อง identifies it)

**ลงวันที่ (Document date, `date`)**:
The official date printed on the หนังสือ header beside ที่. It is the date the หนังสือ is **ส่ง (issued into circulation)** — stamped at `action_send`, re-stamped on each re-send — **not** the create-draft date, so a draft held over the ปีงบประมาณ boundary is dated in the new year when actually sent. Owner-adjustable in a later phase.
_Avoid_: the create/draft timestamp; the completion date (the number's ปีงบ comes from completion, ลงวันที่ from send — they coincide because a หนังสือ never straddles a fiscal-year boundary)

### Signing & record

**ผู้จัดทำ/ผู้ส่ง step (originator, `is_originator`)**:
The mandatory, locked **first Routing Step** — the หนังสือ's ผู้จัดทำ/ผู้ส่ง. Present from creation (row 1); it **cannot be removed** and only its **verb** is editable (a per-document default — signing by default). It is **auto-completed at send** (ส่ง); whether it **renders a signature depends on its verb's `show_signature`** (ADR-0008): a **signing drafter** (ลงนามผู้จัดทำ, show_signature ✓) puts the sender's signature on the document, while a **non-signing drafter** (จัดทำ/ร่าง, show_signature ✗ — e.g. a เจ้าหน้าที่ธุรการ who ร่าง but does not sign, leaving the หัวหน้าส่วนงาน to ตรวจสอบ + ลงนามส่งออก) has only their name in the Route, **no signature**. Either way the originator is **excluded from `has_signed` / strongest-verb** — an originator step is not an approval, so the sender may still **ดึงกลับ / ยกเลิกการส่ง** after sending (until a real approver signs). It is `copy=False` (a duplicate gets a fresh originator for its own sender). Sending is gated behind a **confirm wizard**.
_Avoid_: assuming the drafter always signs (a non-signing ธุรการ drafter is a first-class case — ADR-0008); counting the originator step as an approval (would block recall); a route that starts with an approver (the ผู้จัดทำ is always first); letting a user delete or re-target it

**ฉบับลงนาม (Signed copy)**:
The **immutable PDF snapshot** frozen when a Document reaches `completed`. From then on portal/print serve this file, never a live render. Before completion, preview renders live (own report, or a delegated origin report).
_Avoid_: attachment, printout

**Signature block**:
The rendered authority line on the Document — the digitized signature image, the signer's name, the Position/target signed in, the **signing date in พ.ศ. — date only, no time**, and any **เกษียน note (ความเห็น)**. The **ชื่อ / ตำแหน่ง / ลายเซ็น are a per-step snapshot frozen at the instant of signing** (`signed_name` / `signed_position_name` / `signed_signature`), captured only for positive-done `show_signature` steps, with the live records (`hr.employee.signature` / `.name`, `signed_as_position_id` else `position_id`) as fallback for legacy / in-flight rows — so a later HR-name change, Position rename, or replaced signature image **never rewrites an already-signed หนังสือ**, on any render path (frozen PDF, live preview, direct-origin print) — ADR-0009. **No verb heading**; **one signature per row, right-aligned, stacked downward**. Composed for **every positive-done `show_signature` step** (the signing ผู้จัดทำ + เห็นชอบ + ลงนาม-อนุมัติ) in **one uniform format** (ADR-0008) — endorsers are shown as signatures too, **not** split into a separate เกษียน table; a non-signing step (ตรวจสอบ / พิจารณา / ส่งต่อ, a non-signing ผู้จัดทำ) renders **nothing** here. The academic prefix (`hr.employee.academic_standing_title`), the รักษาการแทน capacity, and the **e-sign metadata line** (time-of-day, the "Non-PKI Server Sign-LN" method label, the Signature Code) are all **phase-2** — the metadata line lands with PKI; when the academic prefix lands it is snapshotted here too (ADR-0009).
_Avoid_: signature (reserve for the act/data, not the rendered block); splitting endorsers into a separate table; rendering a non-`show_signature` step as a signature; **dereferencing name / position / signature live for a signed step** (use the signing snapshot — ADR-0009); printing the sign-method label / Signature Code / time-of-day before PKI exists

**เกษียน trail**:
The accumulated endorsement/signing history (who, when, in what capacity, with what comment). As of **ADR-0008 it is audit-only** — kept on the Routing Steps + chatter and visible in the Route, **no longer rendered onto the official document** (the document shows **signatures only** — the `show_signature` steps). A signing step's own ความเห็น still shows **under its signature block**, but non-signing checks (ตรวจสอบ / พิจารณา / ส่งต่อ) leave no mark on the letter.
_Avoid_: history, log; printing the trail on the official document (superseded — ADR-0008); rendering **backward-move** events (ดึงกลับ / ยกเลิกการส่ง / ตีกลับ / ปฏิเสธ) anywhere on the หนังสือ — those are internal routing history kept in the audit/chatter with their required reason

### Access

**Route visibility**:
Who may read a Document — the **sender**, plus the snapshot actors of any step that is **active or completed**. Steps not yet reached (waiting/future) grant **no** visibility, even if pre-seeded with a named person — you don't see a หนังสือ before it routes to you. Acting is permitted only to the actor of an *active* step. ชั้นความลับ (secrecy) and its need-to-know restriction are **phase-2** — not modeled in v1 (the interim display-label field was removed); v1 keeps manager-see-all. Acting is backend-first in v1, but the act-on-step API is designed token-ready so phase-2 can add passwordless **magic-link** approval from email. **This หนังสือ read access alone governs the official report/preview**: a recipient renders the letter (and sees the origin *reference* on it) **even without rights on the origin record** — the render resolves the origin under `sudo` (ADR-0007). Opening the origin *record itself* (`action_view_origin`) still needs origin rights.
_Avoid_: recipient-only access (the old `recipient_ids.user_id` rule that hid documents from Position/ธุรการหน่วยงาน actors); gating the report/preview on origin-record access (the หนังสือ's own ACL governs — ADR-0007)

### Notifications & inbox

The inbox is **two distinct surfaces**, deliberately not the same set:

**กล่องหนังสือเข้า (Incoming box)**:
The user's **persistent mailbox** — every หนังสือ that has **reached them via the route**, i.e. a step whose snapshot holders include them has activated. A หนังสือ only *enters* once its step actually reaches the user (waiting/future steps grant nothing — "ต้องรอถึง step ก่อนถึงจะเข้า"), and it **stays after they act and after the whole route finishes** (completed / rejected / cancelled). The backend menu. Each row shows the per-person read status / วันที่ได้รับ / เพื่อดำเนินการ, keyed on the step that reached the user (see สถานะการอ่าน). Membership is by *reach*, never by read/unread or by pending action.
_Avoid_: equating it with the Action tray (that is only the awaiting-action subset); read/unread as a membership rule

**Action tray (systray)**:
The top-bar systray notification of หนังสือ **awaiting the current user's action** — the transient subset with an *active* step assigned to them; it **clears as soon as they act**. Pushed realtime over the bus when a step activates/clears, alongside a native `mail.activity` per active *gating* step. Always reflects Route visibility.
_Avoid_: treating it as an archive — it is a live "to-do", not the incoming history (that is the Incoming box)

**สถานะการอ่าน (Read status, `sarabun.step.recipient`)**:
Per-person tracking of whether a holder has **opened** the หนังสือ — รอการเปิดอ่าน (unread) / เปิดอ่านแล้ว (read) — shown per row in the Incoming box, keyed on **the step that reached the user** (their active step, or once they have acted, their most recent completed step). **วันที่ได้รับ** is the per-person timestamp when the step reached that holder (their own recipient row — may be later than the step's activation under delegation). Tracked **individually even when one target has several holders** (each ธุรการหน่วยงาน clerk / co-holder carries their own row). Opening is informational and distinct from acting: **เปิดอ่านแล้ว ≠ รับทราบ** (opening the document is not performing the รับทราบ verb). รอการส่งต่อ (pending-forward) is a reserved state, unused in v1.
_Avoid_: conflating read status with the รับทราบ step verb, or with incoming-box membership

### Classification

**Document kind**:
The behaviour/format axis of a Document — `memo` (บันทึกข้อความ), `circular` (หนังสือเวียน), `from_record` (spawned from an origin). A small dev-extensible set that drives report template, numbering and routing rules. **v1 focuses on `from_record`** (origin-driven e-flow, the live use today); memo/circular are carried by the same engine but their manual-compose UX comes later (หนังสือภายนอก/คำสั่ง/ประกาศ are phase-2 kinds).
_Avoid_: the old hardcoded `code` selection that doubled as both behaviour key and identifier

**Document type (`sarabun.document.type`)**:
An **admin-configurable** record naming a concrete type ("บันทึกข้อความกองคลัง") and binding its default route / template, pointing at one Document kind. The configurable layer above the fixed kind axis. (The register/number sequence is resolved per **ส่วนงาน**, not per type — see Register.) The kind axis still exists on the model but is hidden from the หนังสือ form (only `from_record` is exercised in v1).
_Avoid_: treating type and kind as one field; expecting the type to carry its own number series

**ชั้นความเร็ว / ชั้นความลับ (Speed / Secrecy levels)**:
Records-regulation handling labels — ชั้นความเร็ว (ปกติ / ด่วน / ด่วนมาก / ด่วนที่สุด) and ชั้นความลับ (ปกติ / ลับ / ลับมาก / ลับที่สุด). **Phase-2** — not modeled in v1 (the interim fields were removed); v1 has no urgency flag and keeps manager-see-all (see Access).
_Avoid_: modeling these as routing behaviour (they are header/handling labels, not gating)

### Attachments & links

**อ้างถึง (Reference)**:
Links to prior หนังสือ (m2m `sarabun.document`) plus free-text lines for letters outside the system (e.g. "หนังสือ อว 6801/123 ลว 1 พ.ค."). Distinct from the **origin link** (which connects to the spawning ERP record).
_Avoid_: the dropped `sarabun.reference` hardcoded PR/PO/budget link — that was *related ERP records*, not อ้างถึง

**สิ่งที่ส่งมาด้วย (Enclosure)**:
An **ordered, described** attachment of the Document, rendered as a numbered list ("สิ่งที่ส่งมาด้วย ๑. …") per the regulation.
_Avoid_: bare attachment with no order or caption

### Header

**เรียน (Addressee) + คำขึ้นต้น (Prefix)**:
The ceremonial recipient printed on the หนังสือ header — its **own field** (free multi-line text), set manually or by the origin, and opened by a configurable **คำขึ้นต้น (salutation, `sarabun.addressee.prefix`)** — เรียน today, with กราบทูล / เสนอ / ยื่นต่อ … as configurable alternatives. Deliberately separate from the routing actors (you address "เรียน คณบดี" while the หนังสือ still routes clerk → หัวหน้างาน → คณบดี). (**ผ่าน** "เรียน X ผ่าน Y", and auto-suggesting the addressee from the final ลงนาม-อนุมัติ step's Position, are **phase-2** — not modeled in v1.)
_Avoid_: the old free-text `recipient` / "To" that floated free of routing; conflating the addressee with the people who actually act; a hardcoded "เรียน" label (the salutation is configurable)

**เนื้อหา (Content / body, `content`)**:
The หนังสือ's own body — free **rich text** typed on the form — the letter body **only for a no-source Document** (composed memo/circular). For a `from_record` / has-source Document it is **not rendered on the official PDF at all**: the source report is the self-contained body (the removed cover sheet used to render `content` as a covering note above the origin report — that covering note is gone). v1 is plain rich text; the full regulation บันทึกข้อความ layout is phase-2.
_Avoid_: rendering `content` on a has-source PDF (covering note removed with the cover sheet); assuming the body always comes from the origin report; treating this rich-text box as the regulation memo template

**หมายเหตุ (Remark, `remark`)**:
An **optional internal note** (rich text) on the หนังสือ, captured after the body — **not part of the letter body** and not rendered as the official content. For working notes.
_Avoid_: conflating หมายเหตุ with เนื้อหา (content) — remark is internal, content is the letter itself

**Endorsement block (บล็อกลายเซ็น)**:
The reusable rendered **tail** of an official document — the **Signature block(s)** (as of ADR-0008, **signatures only**; the เกษียน trail is no longer printed). Owned by agx_sarabun as a single QWeb layout that the **source report `t-call`s at its own end**: the origin *embeds* sarabun's block; sarabun no longer wraps the origin. It is **self-limiting** — it renders only positive-done `show_signature` steps, so a draft shows nothing. The Document to render is resolved from the origin via `active_sarabun_document_id`. The old prepended **ใบปะหน้าสารบรรณ (cover sheet)** and the front-merge of a separate sarabun page are **removed**.
_Avoid_: printing the เกษียน trail here (signatures only — ADR-0008); cover sheet / ใบปะหน้า prepended to the origin; PDF-merging a separate sarabun page in front of the body; re-keying origin content into a memo template

**Standalone document report (no-source)**:
For a Document with **no source report** (a composed บันทึกข้อความ / หนังสือเวียน), agx_sarabun renders its **own** whole document — official header (หน่วยงาน / ที่ / วันที่ / เรื่อง / เรียน) + **เนื้อหา (content)** body + the same Endorsement block — as the official PDF. Today every real Document has a source report, so this is a **planned seam**; the full regulation บันทึกข้อความ layout (ครุฑ, ด่วน label, หมายเหตุ footer, in-body hyperlinks — per the KMITL example) is **still to be designed**.
_Avoid_: assuming every Document has a source body; reusing the removed cover-sheet-merge for this path
