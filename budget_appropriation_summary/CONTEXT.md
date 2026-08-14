# Budget Appropriation Summary — Context

Institution-wide roll-up of unit budget appropriations for one fiscal year and
one money source, producing the government F-series summary reports and, finally,
one authoritative watermarked deliverable.

## Glossary

- **สรุปภาพรวมสถาบัน (Master Summary)** — `budget.appropriation.master.summary`.
  The institution-wide roll-up, scoped to one fiscal year × one **source**
  (แหล่งเงิน), that gathers every unit **Compilation** and renders the F-series
  summary reports (F2, F4-P/W, F5-P/W, F7-F11).

- **รวมเล่มหน่วยงาน (Compilation)** — `budget.appropriation.compilation`. One
  organisational unit's bound volume of appropriations (revenue + expense) that
  feeds into a Master Summary. A Master Summary confirms only once all its
  Compilations are confirmed.

- **ไฟล์ฉบับสมบูรณ์ (Final Document)** — the clean PDF re-uploaded into the Master
  Summary after being exported and formatted **outside the system** (page breaks
  fixed, cover/insert pages and references added). It is the raw upload and the
  source of truth for the deliverable; it carries **no** watermark.

- **ลายน้ำ PDF (Watermark PDF)** — a purpose-built, transparent single-page
  overlay PDF uploaded per Master Summary. It is stamped **on top of** every page
  of the Final Document. Being an overlay, it must have a transparent background
  so it never obscures content and stays visible even over opaque/scanned pages.

- **ฉบับเผยแพร่พร้อมลายน้ำ (Published Final)** — the generated copy produced by
  overlaying the Watermark PDF onto every page of the Final Document. This is the
  distributed official file. It is (re)generated on demand from the clean Final
  Document, so it is never double-stamped and always reflects the current
  Watermark PDF.
