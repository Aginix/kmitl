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

Step verbs are **admin-configurable master data** (`sarabun.verb`); the three built-ins below are seeded and referenced by the engine via their **xmlid** (`agx_sarabun.verb_*`) — there is no separate identity/code field. Admins may add or relabel verbs. The internal behaviour model (how a verb drives gating / completion / signing) is **provisional, pending review after real use**.

**รับทราบ (Acknowledge)**:
For information; the actor confirms receipt. **Non-gating** — does not block the chain and may run in parallel.

**เห็นชอบ (Endorse)**:
Mid-chain gatekeeping — the actor reviews and passes upward with an opinion. **Gating**; may also ตีกลับ or ปฏิเสธ.

**ลงนาม-อนุมัติ (Sign-Approve)**:
The authority's decision **and** signature, made in the capacity of the step's target Position. **Gating**. Signing and approving are one verb for now (split deferred until a real case appears).
_Avoid_: "approve" on its own (it carries the signature)

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
The **sender** pulls a circulating Document **back to an editable state, keeping its registered number**, to revise and re-send (แบบ pull-back-to-edit). The prior routing chain is archived as history and the chain restarts on re-send; the Document lands in state `returned` — behaving as a self-initiated ตีกลับ-to-sender. Permitted **only while no ลงนาม-อนุมัติ step has occurred**. Contrast ยกเลิกการส่ง: ดึงกลับ *keeps* the number and expects a re-send.
_Avoid_: เรียกคืน (one term now — ดึงกลับ); cancel / void-the-number (that is ยกเลิกการส่ง, a different act)

**ยกเลิกการส่ง (Cancel-send)**:
The **sender** withdraws a circulating Document **terminally** — it lands in state `cancelled` and its registered number is **voided** (a permanent gap; see Voided number). For "this send should never have happened", not "let me fix it" (that is ดึงกลับ). Permitted **only while no ลงนาม-อนุมัติ step has occurred**; once a signature exists the Document is part of the record and withdrawal instead requires issuing a cancellation หนังสือ.
_Avoid_: ดึงกลับ (ดึงกลับ keeps the number and re-sends; ยกเลิกการส่ง voids it and ends the Document); recall / เรียกคืน (the old name conflated these two acts)

**Voided number (เลขยกเลิก)**:
A registered document number whose Document was rejected or cancelled — kept as a **permanent gap, never reissued**, so the register stays auditable.
_Avoid_: released number, reusable number

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
The act of assigning a Document its official running number from a sequence. In v1 it fires **automatically at send** (draft → circulating), but is kept a *distinct event* so a ธุรการหน่วยงาน clerk-gate can be inserted in phase 2. The sequence is resolved automatically from the **sender ส่วนงาน** — each ส่วนงาน issues from **one register shared across all its document types** (a หน่วยงาน keeps a single running number series; the earlier per-`(ส่วนงาน × type)` split was dropped on feedback), not one institute-wide pool; if no sequence is configured for that unit the send is **blocked with a clear error**, never silently numbered from a default. Numbers reset per **ปีงบประมาณ (fiscal year, Oct–Sep)** by default and render in พ.ศ. A number is allocated atomically (row-locked) and never recycled (see Voided number).
_Avoid_: numbering (reserve "register" for the official, audited act)

### Signing & record

**ฉบับลงนาม (Signed copy)**:
The **immutable PDF snapshot** frozen when a Document reaches `completed`. From then on portal/print serve this file, never a live render. Before completion, preview renders live (own report, or a delegated origin report).
_Avoid_: attachment, printout

**Signature block**:
The rendered authority line on the Document — the digitized signature image (`hr.employee.signature`, from `hr_employee_digitized_signature`), the signer's name, the Position signed in (`signed_as_position_id`, may wrap to several lines), and the **signing date in พ.ศ. — date only, no time**. Composed once per completed ลงนาม-อนุมัติ step from the snapshot actor. The academic prefix (`hr.employee.academic_standing_title`), the รักษาการแทน capacity, and the **e-sign metadata line** (time-of-day, the "Non-PKI Server Sign-LN" method label, the Signature Code) are all **phase-2** — the metadata line lands with PKI.
_Avoid_: signature (reserve for the act/data, not the rendered block); printing the sign-method label / Signature Code / time-of-day before PKI exists

**เกษียน trail**:
The accumulated endorsement/signing history (who, when, in what capacity, with what comment) **rendered onto the official document** — not hidden in chatter. Scoped to positive endorsement/signing (เห็นชอบ / ลงนาม-อนุมัติ) only.
_Avoid_: history, log; rendering **backward-move** events (ดึงกลับ / ยกเลิกการส่ง / ตีกลับ / ปฏิเสธ) onto the official document — those are internal routing history kept in the audit/chatter with their required reason, never printed on the หนังสือ

### Access

**Route visibility**:
Who may read a Document — the **sender**, plus the snapshot actors of any step that is **active or completed**. Steps not yet reached (waiting/future) grant **no** visibility, even if pre-seeded with a named person — you don't see a หนังสือ before it routes to you. Acting is permitted only to the actor of an *active* step. ชั้นความลับ (secrecy) and its need-to-know restriction are **phase-2** — not modeled in v1 (the interim display-label field was removed); v1 keeps manager-see-all. Acting is backend-first in v1, but the act-on-step API is designed token-ready so phase-2 can add passwordless **magic-link** approval from email.
_Avoid_: recipient-only access (the old `recipient_ids.user_id` rule that hid documents from Position/ธุรการหน่วยงาน actors)

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

**Endorsement block (บล็อกลายเซ็น + เกษียน)**:
The reusable rendered **tail** of an official document — the **เกษียน trail** + the **Signature block(s)**. Owned by agx_sarabun as a single QWeb layout that the **source report `t-call`s at its own end**: the origin *embeds* sarabun's block; sarabun no longer wraps the origin. The Document to render is resolved from the origin via `active_sarabun_document_id`. The old prepended **ใบปะหน้าสารบรรณ (cover sheet)** and the front-merge of a separate sarabun page are **removed**.
_Avoid_: cover sheet / ใบปะหน้า prepended to the origin; PDF-merging a separate sarabun page in front of the body; re-keying origin content into a memo template

**Standalone document report (no-source)**:
For a Document with **no source report** (a composed บันทึกข้อความ / หนังสือเวียน), agx_sarabun renders its **own** whole document — official header (หน่วยงาน / ที่ / วันที่ / เรื่อง / เรียน) + **เนื้อหา (content)** body + the same Endorsement block — as the official PDF. Today every real Document has a source report, so this is a **planned seam**; the full regulation บันทึกข้อความ layout (ครุฑ, ด่วน label, หมายเหตุ footer, in-body hyperlinks — per the KMITL example) is **still to be designed**.
_Avoid_: assuming every Document has a source body; reusing the removed cover-sheet-merge for this path
