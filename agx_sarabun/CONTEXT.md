# e-Saraban (สารบรรณอิเล็กทรอนิกส์)

Electronic official-correspondence (งานสารบรรณ) for KMITL. The **หนังสือ (Document) is the protagonist**: it is registered, numbered per the records regulation, and routed through an approval/endorsement chain. A heavy emphasis sits on the **approval-routing engine** — how a document flows through people/positions for เกษียน → เสนอ → ลงนาม → รับทราบ. Integration with other modules (e.g. a purchase request that spawns a memo) is a *secondary adapter*, not the centre of gravity.

## Language

**Document (หนังสือ / เอกสาร, `sarabun.document`)**:
The protagonist — one official correspondence item that is registered, numbered, and routed. Everything else (route, steps, register entries) hangs off it.
_Avoid_: ticket, request, approval (those describe the routing, not the หนังสือ)

**Origin record**:
A business object in another module (e.g. `purchase.request`) that spawns a Document and is notified of its outcome via callbacks. It is the *adapter* side, never the protagonist — the engine must not bend toward approval semantics to serve it. One origin may own **several** Documents over time (a rejected one is superseded by a duplicated new draft — see ADR-0002), so the relation is 1:N; the mixin exposes all of them plus an `active_sarabun_document_id` pointer to the current live one.
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
An administrative/authority position — the **primary routing target** and the capacity a document is signed in (คณบดี, ผอ.กอง, อธิการบดี). Purpose-built for e-Saraban, distinct from `hr.job` (employment position) and from academic rank. Resolves to its current **holder(s)** when a step becomes *active*, and that resolved person-set is **snapshotted** onto the step so later org changes never rewrite history. (รักษาการ/มอบอำนาจ — acting & delegated authority — is a planned phase-2 seam; interim, add the acting user as a temporary holder.)
_Avoid_: role, hr.job, job position

**Academic rank (วุฒิ/คำนำหน้าทางวิชาการ)**:
A person's scholarly title (ศ., รศ., ผศ., ดร.) shown in the signature block **for display only** — never a routing target or signing authority. The old `role_category` wrongly merged this with Position.
_Avoid_: position, role

**Targeting mode**:
What a Routing Step points at — exactly one of **Position** (canonical), **Person** (a specific user), or **Unit** (a department's สารบรรณกลาง / central registry, used mainly for incoming หนังสือ).
_Avoid_: the old `recipient_type` vocabulary "user / department / role"

### Step verbs (what a step requires)

**รับทราบ (Acknowledge)**:
For information; the actor confirms receipt. **Non-gating** — does not block the chain and may run in parallel.

**เห็นชอบ (Endorse)**:
Mid-chain gatekeeping — the actor reviews and passes upward with an opinion. **Gating**; may also ตีกลับ or ปฏิเสธ.

**ลงนาม-อนุมัติ (Sign-Approve)**:
The authority's decision **and** signature, made in the capacity of the step's target Position. **Gating**. Signing and approving are one verb for now (split deferred until a real case appears).
_Avoid_: "approve" on its own (it carries the signature)

### Dispositions (how the active actor responds)

The set of moves available at an active step, subject to authority: **complete** (perform the required verb) · **เกษียนสั่งการ (Direct)** (I acted, now insert the next step) · **มอบหมาย (Delegate)** (I will not act — X performs *this* step instead) · **ตีกลับ (Return)** (send back for revision) · **ปฏิเสธ (Reject)** (terminal negative).
_Avoid_: treating มอบหมาย and เกษียนสั่งการ as the same move — Delegate reassigns *this* step, Direct inserts the *next*.

### Lifecycle

**Circulating (กำลังดำเนินการ)**:
A Document in flight along its Route. Renamed from the old `sent` to capture "moving through the chain", not "delivered once".
_Avoid_: sent, in transit

**Return (ตีกลับ)**:
Send a circulating Document back for revision. The returner picks the destination — default is back to the sender with the chain **restarted**, but an earlier step may be chosen to **resume** from. Lands the Document in state `returned` (revisable like a draft, but the prior chain is kept as history).
_Avoid_: reject (Return is recoverable; Reject is terminal)

**Recall (เรียกคืน)**:
The sender withdraws a circulating Document — permitted **only while no ลงนาม-อนุมัติ step has occurred**. Once a signature exists the Document is part of the record; withdrawal then requires issuing a cancellation หนังสือ, not a recall.
_Avoid_: cancel (cancel is the resulting state; recall is the act)

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
When a step targets a Position or Unit held by several people, the **first holder to act completes it** on the group's behalf. "Everyone must act" is expressed as several parallel steps instead, never as a quorum rule on one step. A single ปฏิเสธ within a co-approval Stage rejects the whole Document immediately.
_Avoid_: all-must-approve quorum on a single step

### Numbering

**ลงทะเบียน (Register)**:
The act of assigning a Document its official running number from a sequence. In v1 it fires **automatically at send** (draft → circulating), but is kept a *distinct event* so a สารบรรณกลาง clerk-gate can be inserted in phase 2. The sequence is resolved automatically from the **sender ส่วนงาน** — each ส่วนงาน issues from **one register shared across all its document types** (a หน่วยงาน keeps a single running number series; the earlier per-`(ส่วนงาน × type)` split was dropped on feedback), not one institute-wide pool; if no sequence is configured for that unit the send is **blocked with a clear error**, never silently numbered from a default. Numbers reset per **ปีงบประมาณ (fiscal year, Oct–Sep)** by default and render in พ.ศ. A number is allocated atomically (row-locked) and never recycled (see Voided number).
_Avoid_: numbering (reserve "register" for the official, audited act)

### Signing & record

**ฉบับลงนาม (Signed copy)**:
The **immutable PDF snapshot** frozen when a Document reaches `completed`. From then on portal/print serve this file, never a live render. Before completion, preview renders live (own report, or a delegated origin report).
_Avoid_: attachment, printout

**Signature block**:
The rendered authority line on the Document — the signer's name, the Position signed in, the digitized signature image (from `hr_employee_digitized_signature`), and datetime. The academic prefix (`hr.employee.academic_standing_title`) and รักษาการแทน capacity are phase-2.
_Avoid_: signature (reserve for the act/data, not the rendered block)

**เกษียน trail**:
The accumulated endorsement/signing history (who, when, in what capacity, with what comment) **rendered onto the official document** — not hidden in chatter.
_Avoid_: history, log

### Access

**Route visibility**:
Who may read a Document — the **sender**, plus the snapshot actors of any step that is **active or completed**. Steps not yet reached (waiting/future) grant **no** visibility, even if pre-seeded with a named person — you don't see a หนังสือ before it routes to you. Acting is permitted only to the actor of an *active* step. ชั้นความลับ need-to-know restriction is **phase-2**; v1 treats secrecy as a display label and keeps manager-see-all. Acting is backend-first in v1, but the act-on-step API is designed token-ready so phase-2 can add passwordless **magic-link** approval from email.
_Avoid_: recipient-only access (the old `recipient_ids.user_id` rule that hid documents from Position/Unit actors)

### Notifications

**Inbox (กล่องหนังสือเข้า)**:
The set of หนังสือ **awaiting the current user's action** — documents with an *active* step whose snapshot holders include them. Surfaced as a top-bar **systray tray** (live count + list, pushed realtime over the bus when a step activates/clears) plus a matching menu, alongside a native `mail.activity` raised per active *gating* step. It always reflects Route visibility, so it shows only หนังสือ the user is entitled to see and act on.
_Avoid_: read/unread mailbox semantics — the inbox means "awaiting my action", not "unread mail"

### Classification

**Document kind**:
The behaviour/format axis of a Document — `memo` (บันทึกข้อความ), `circular` (หนังสือเวียน), `from_record` (spawned from an origin). A small dev-extensible set that drives report template, numbering and routing rules. **v1 focuses on `from_record`** (origin-driven e-flow, the live use today); memo/circular are carried by the same engine but their manual-compose UX comes later (หนังสือภายนอก/คำสั่ง/ประกาศ are phase-2 kinds).
_Avoid_: the old hardcoded `code` selection that doubled as both behaviour key and identifier

**Document type (`sarabun.document.type`)**:
An **admin-configurable** record naming a concrete type ("บันทึกข้อความกองคลัง") and binding its default route / template, pointing at one Document kind. The configurable layer above the fixed kind axis. (The register/number sequence is resolved per **ส่วนงาน**, not per type — see Register.)
_Avoid_: treating type and kind as one field; expecting the type to carry its own number series

### Attachments & links

**อ้างถึง (Reference)**:
Links to prior หนังสือ (m2m `sarabun.document`) plus free-text lines for letters outside the system (e.g. "หนังสือ อว 6801/123 ลว 1 พ.ค."). Distinct from the **origin link** (which connects to the spawning ERP record).
_Avoid_: the dropped `sarabun.reference` hardcoded PR/PO/budget link — that was *related ERP records*, not อ้างถึง

**สิ่งที่ส่งมาด้วย (Enclosure)**:
An **ordered, described** attachment of the Document, rendered as a numbered list ("สิ่งที่ส่งมาด้วย ๑. …") per the regulation.
_Avoid_: bare attachment with no order or caption

### Header

**เรียน (Addressee)**:
The ceremonial recipient printed on the หนังสือ header — its **own field**, set manually or by the origin (with an optional suggest from the final ลงนาม-อนุมัติ step's Position). Deliberately separate from the routing actors (you address "เรียน คณบดี" while the หนังสือ still routes clerk → หัวหน้างาน → คณบดี). An optional **ผ่าน (Through)** free-text captures "เรียน X ผ่าน Y".
_Avoid_: the old free-text `recipient` / "To" that floated free of routing; conflating the addressee with the people who actually act

**เนื้อหา (Content / body, `content`)**:
The หนังสือ's own body — free **rich text** typed on the form. For a composed memo/circular it **is** the letter body; for a `from_record` Document it is an **optional covering note** rendered on the cover **above** the appended origin report. v1 is plain rich text — the full regulation บันทึกข้อความ layout (ครุฑ, formatted body per ระเบียบ) is still phase-2.
_Avoid_: assuming the body always comes from the origin report (from_record); treating this rich-text box as the regulation memo template

**ใบปะหน้าสารบรรณ (Cover sheet)**:
The system-rendered front page — official header (number / date / เรื่อง / เรียน / ผ่าน), the **เนื้อหา (content) body**, the signature block, and the เกษียน trail. For a `from_record` Document the origin's report is appended after it as further body; the frozen ฉบับลงนาม is the merge. A full reformat of origin content into a บันทึกข้อความ body is deferred.
_Avoid_: re-keying origin content into a memo template
