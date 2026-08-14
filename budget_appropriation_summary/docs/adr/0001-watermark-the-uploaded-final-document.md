# Watermark the uploaded Final Document, not the report prints

The F-series summary prints have page breaks and layout that must be hand-fixed
outside the system, so the authoritative deliverable is the re-uploaded **Final
Document**, not the auto-generated PDF. We therefore watermark the uploaded Final
Document — overlaying a user-supplied, transparent single-page **Watermark PDF**
on top of every page (scaled to each page) into a separate **Published Final**
(`final_document_watermarked`), generated on demand so it never double-stamps —
rather than stamping the report renderer. The feature lives in the bridge module
`budget_appropriation_summary_watermark` (not base) because
`budget_appropriation_summary` is already in production and we want the deployed
module untouched; only the base-owned `final_document` field stays in base.

## Considered Options

- **Watermark the report prints** (reportlab text/logo generator + OCA
  `report_qweb_pdf_watermark`, plus CSS on the HTML preview) — built first in
  PR #1090, then rejected: the prints are never the final artifact and can't fix
  page breaks; it also needed two render paths (server PDF merge + browser CSS)
  kept in sync, plus an OCA dependency.
- **Fold into base `budget_appropriation_summary`** — rejected: base is deployed;
  a bridge keeps the live module free of new schema / version / view churn.

## Consequences

- Base gains only `final_document`; all watermark schema and logic is in the
  bridge. Uninstalling the bridge leaves the clean Final Document intact.
- The Watermark PDF **must have a transparent background** (it is overlaid on
  top); an opaque watermark would hide content.
- The watermark is scaled **uniformly** (aspect-preserving) — never stretched.
  **Portrait** pages anchor it to the **bottom-right corner** so a corner-placed
  mark (e.g. a council-resolution stamp) stays flush; **landscape** pages
  **centre** it, so a portrait watermark sits balanced in the middle instead of
  being shoved to one side. Trade-off: when the watermark and page differ in
  size/aspect (e.g. a Letter watermark on an A4 page), the leftover gap means a
  centred element (a seal) sits slightly off-centre on portrait pages. For a
  pixel-perfect 1:1 overlay, author the Watermark PDF at the same page size as
  the Final Document.
- Published Final is a plain downloadable field — no auto-distribution, chatter
  attachment, or e-Saraban flow. It auto-clears when either input changes.
