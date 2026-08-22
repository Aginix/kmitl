# A from-record หนังสือ may render through the no-source layout with a live body fragment

**Amends [ADR-0007](0007-official-pdf-source-embeds-endorsement-block.md).** ADR-0007 assumed every real (from-record) Document delegates its whole body to the origin's own report — which carries its *own* header and `t-call`s the endorsement block at its tail, while `content` is dropped. In practice that forces each origin report to duplicate สารบรรณ's header (เลขที่ / หน่วยงาน / เรียน / วันที่ / อ้างถึง) and re-embed the signature block, and gives the user no editable body.

We add a **second composition option** for a from-record Document, without removing the delegation path: the Document renders through สารบรรณ's **own no-source report** (`report_sarabun_document`) — so สารบรรณ owns the header and the endorsement block — and the origin contributes only a **live body fragment** rendered in a new slot between `content` and the signatures:

```
หัวสารบรรณ            ← สารบรรณ (live, from sarabun.document fields)
content (บันทึกนำ)     ← optional editable Html; per-consumer opt-in
เนื้อจากต้นเรื่อง       ← NEW slot: origin's live body fragment (data/tables)
ลายเซ็น (endorsement) ← สารบรรณ
```

The new engine seam is one hook + one render point:

- `sarabun.document.mixin._get_sarabun_body_template()` → an XML id of a QWeb template rendering the origin's live body, or `False` (default). The origin record is passed in as `o`.
- `report_sarabun_document` resolves the origin (sudo browse of `origin_model`/`origin_res_id`) and `t-call`s that template **after** the `content` block and **before** the endorsement block. The fragment renders regardless of `include_content` (it is data, not the covering note).

A from-record Document reaches this path by overriding `_get_sarabun_report_action()` → `False` (so `_get_delegated_report_action()` yields nothing and `_render_official_pdf` falls to `report_sarabun_document`). Editable body (`content`) and the live fragment are **both per-consumer opt-in**: a consumer that wants neither stays on the ADR-0007 delegation path unchanged.

## First adopter: agx_approval (คำขออนุมัติค่าใช้จ่าย)

The driver is that the approval report lacked สารบรรณ's header fields and would have had to reimplement them. `agx_approval_sarabun` adopts this model:

- `_get_sarabun_report_action()` → `False`.
- **content = ตัวบรรยาย, editable** — seeded once from the record (ผู้ขออนุมัติ / ผู้รับผิดชอบ / ประเภท / รายละเอียด / ระยะเวลา) at `action_submit_to_sarabun`, then owned by the user. **Policy 5A:** no auto-regenerate on record change; drift is tolerated because บรรยาย is low-integrity (no budget numbers) and the edit window is `draft` + `returned` only, after which the หนังสือ freezes. `include_content` defaults ON for this consumer.
- **เนื้อจากต้นเรื่อง = the tables, live** — budget details / expense plan / participants / actual allocation, via `_get_sarabun_body_template()`. Rendered live and **not** editable, so the official หนังสือ can never show budget/allocation numbers that diverge from the reserved commitment or the disbursement it feeds.

## Considered options

- **Snapshot the whole body into `content` (rejected)** — least engine work, but freezes the authoritative tables into editable Html: numbers go stale on record change and can be edited to diverge from the budget commitment / disbursement. Rejected on governance grounds — the printed หนังสือ is the official record.
- **Keep delegation, restyle the origin report to draw สารบรรณ's header (rejected)** — no snapshot, always live, but every origin report must duplicate the header logic and gives no editable body. Rejected as the duplication ADR-0007 already causes.
- **Split: content = editable บรรยาย, fragment = live tables (accepted)** — the extra hook + template split buys editable prose *and* live-accurate numbers, and generalises to other consumers.

## Consequences

- **agx_approval retires its standalone report** (option 6B): `report_approval_request_document`, its `action_report_approval_request` binding, and the `report_approval_endorsement.xml` inject are removed — the หนังสือ is the only document, and the endorsement is สารบรรณ's `t-call` again. **No pre-submit preview**: the full letter (with header) exists only once the หนังสือ is created at submit; a `draft`/`to_send` request has no printable official document, which matches "approval is routed through e-Saraban."
- The origin's body-fragment template must **not** repeat the header block (เลขที่ / วันที่ / หน่วยงาน / เรื่อง) — สารบรรณ renders those. It carries only บรรยาย-less data (approval keeps บรรยาย in `content`).
- **Origin resolved under sudo** in the no-source report, same rationale as ADR-0007 — a Route recipient without origin rights still gets the correct fragment.
- The delegation path (ADR-0007) **stays** for other consumers (purchase_request_sarabun, disbursement_sarabun, budget_transfer_sarabun, purchase_request_approval) until/unless they migrate. This is additive.
- Pre-production (whole สารบรรณ stack on the feature branch, not in `origin/16.0`) — no migration, no version bump.
