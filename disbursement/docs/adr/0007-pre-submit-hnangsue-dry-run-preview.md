# A dry-run preview of the หนังสือ before Submit to Sarabun

agx_sarabun ADR-0015 says **no pre-submit preview**: the full letter exists only
once the หนังสือ is created at submit. For disbursement, users want to check the
หนังสือ — header, บันทึกนำ, the request's body table — before they send it, and
the old portal "Preview" (ADR 0006) only showed the standalone ใบขอเบิก.

## Decision

`disbursement_sarabun_preview` (auto-installed with `disbursement_sarabun`) adds
a **ดูตัวอย่างเอกสาร** button to the request form, in every state but `cancel`.
This amends ADR-0015 for disbursement only; agx_sarabun is unchanged.

- With a live หนังสือ the button opens that หนังสือ's own preview dialog
  (agx_sarabun ADR-0007).
- Without one it renders a **dry run**: an unsaved `sarabun.document.new()`
  built from `default_get` plus `_prepare_sarabun_document_vals()` (the same vals
  Submit to Sarabun uses), rendered as HTML with the document type's no-source
  report, framed to A4 and watermarked "ตัวอย่าง". It opens in the same dialog,
  a subclass of `SarabunPdfPreview` pointed at
  `/disbursement/request/<id>/sarabun_preview`.

## Why it is safe

- The vals are pure: no number is issued and no route is built at prepare time
  (the number comes at the issuing sign, ADR-0017).
- Nothing is persisted: `new()` writes no row, and the defaults have no side
  effects.
- It is screen-only HTML with a watermark and no signatures, so it cannot be
  mistaken for, or printed as, the official document.
- The route checks the user's read access on the request; the render is sudo, as
  the หนังสือ's own preview is.

## Considered options

- **A TransientModel holding the draft (rejected)** — it writes a row for a
  screen-only view and needs its own cleanup.
- **Preview the standalone ใบขอเบิก (rejected)** — it is not what is sent.
- **Change agx_sarabun (rejected)** — other consumers keep ADR-0015 as is.
