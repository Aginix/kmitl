Adds **เอกสารอ้างอิงเพิ่มเติม** to the loan form: any number of further
documents cited beside the source document — e.g. a หนังสือสารบรรณ backing a
loan for a purchase request (advance_payment ADR-0029).

Each row is either

- an **in-system document** of a supported kind, found by typing its number
  exactly (looked up under sudo, like the source document — the borrower need
  not be able to read it), with ลงวันที่ to tell apart numbers that repeat each
  fiscal year; or
- an **out-of-system document** given by number and/or subject,

optionally with a file. The rows are evidence only: they never drive the
borrowing headroom, the dimensions or the route.

Who may change them, until the agreement is closed or cancelled:

- the borrower may add rows at any time, but remove only the rows they added,
  and only while the request is a draft;
- unit finance (`group_advance_payment_user`) and the loan officer may add and
  remove any row.

Every addition and removal is logged on the agreement.

Each in-system kind comes from a small bridge module, e.g.
`advance_payment_related_document_sarabun`.
