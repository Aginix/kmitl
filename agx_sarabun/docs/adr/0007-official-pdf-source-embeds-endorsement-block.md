# Official PDF: the source report embeds sarabun's endorsement block (no cover sheet)

**Supersedes the composition model in [DESIGN §5.5](../../DESIGN.md).** DESIGN §5.5 built the official PDF as a system-rendered **ใบปะหน้าสารบรรณ (cover sheet)** — official header + เนื้อหา + เกษียน trail + signature block — **PDF-merged in front of** the origin's delegated report, frozen as the ฉบับลงนาม at `completed`. In real use the cover sheet is unwanted: it duplicates a header the source document already carries and forces the signatures onto a separate front page.

We **invert the composition**: instead of *sarabun wraps the origin*, the *origin embeds sarabun's block*.

- agx_sarabun ships **one reusable QWeb layout, `sarabun_endorsement_block`**, that renders the **เกษียน trail + Signature block(s)** for a given `sarabun.document`.
- Each **source report** (owned by the bridge modules) `t-call`s that block at the **end of its own `<div class="page">`**, resolving the Document from the origin via `active_sarabun_document_id`. There is **no PDF merge** and **no cover sheet**.
- For a Document with **no source report** (a composed บันทึกข้อความ / หนังสือเวียน — a planned seam; today every real Document has a source report), agx_sarabun renders its **own** slim standalone document (official header + `content` body + the same block). The full regulation บันทึกข้อความ layout is still to be designed.

The **freeze** (§5.4) is unchanged: `_render_official_pdf` now renders a *single* report (the source report for has-source, the own report for no-source) with no merge step, and the result is frozen into `signed_pdf` at `completed`.

## Considered options

- **Cover-sheet merge (status quo, rejected)** — a separate sarabun page merged in front of the origin body. Rejected: unwanted front page, duplicated header, signatures divorced from the document body.
- **agx_sarabun renders the block as its own report and PDF-merges it after the body (rejected)** — keeps sarabun in control of the block but still merges, forces the block onto a fresh page, and doesn't honour "a QWeb layout used *inside* the source report". Rejected in favour of a `t-call` embedded in the source template so the block flows naturally after the body.

## Consequences

- **Every bridge inherits its own source report** to inject the `t-call` (purchase_request_sarabun, disbursement_sarabun, agx_approval_sarabun, purchase_request_approval). Because the block is rendered *by the source report*, it also appears when the **origin record is printed directly** (not only via the sarabun print path) — accepted.
- **The block is self-limiting**: it renders only `done` + positive-disposition steps (เกษียน from เห็นชอบ, signatures from ลงนาม-อนุมัติ). Empty ⇒ nothing shows. No explicit `state` gate — a draft prints no block, a circulating one shows the partial trail, a completed one shows the full block + signatures.
- **`content` is dropped from the has-source PDF** — the covering note the cover sheet used to render is gone; `content` is the body **only** for the no-source path.
- **Signature block content** (this pass): digitized signature image + signer name (**no academic prefix** — still phase-2) + `signed_as_position_id` + **signing date in พ.ศ., date only**. **No** time-of-day, **no** "Non-PKI Server Sign-LN" method label, **no** Signature Code — all three land with **PKI** (phase-2).
- **Document resolution is `active_sarabun_document_id` (simple)** — correct at freeze (active = self) and for the current 1-live-document reality. A per-render *pinned* document (context/`data`) is deferred until a real multi-document print case appears.
- **Form preview:** the official PDF opens in a **full-page in-app preview** — a `sarabun_pdf_preview` **client action** with a back button to the form — launched from a "ดูเอกสาร (PDF)" header button (shown in every state, incl. a saved draft for ดูก่อนส่ง). An earlier in-form toggle (overlay the form with the `<iframe>`) was dropped as too fragile — it depended on inheriting the `web.FormView` template and matching compiled form-root classes. Requires the PDF controller to serve **`inline`** (today it forces `attachment`).
- **Engine work:** remove `action_report_sarabun_cover` / the cover template's prepend role; add `sarabun_endorsement_block`; repurpose the cover template into the no-source own report; drop the `merge_pdf` step in `_render_official_pdf`; extend the `sarabun_document_form` OWL controller + view for the preview toggle. Pre-production (whole stack is on the feature branch, not in `origin/16.0`) — no migration of frozen copies.
