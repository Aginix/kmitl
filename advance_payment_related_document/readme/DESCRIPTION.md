Adds **เอกสารอ้างอิงเพิ่มเติม** to the loan form: any number of further
documents cited beside the source document — e.g. a หนังสือสารบรรณ backing a
loan for a purchase request (advance_payment ADR-0029).

The generic mechanism (kinds, lookup, snapshot, ถูกอ้างอิงโดย) is `agx_related_document`; this
module only puts it on the loan and keeps the loan's own rules. The rows are evidence only: they
never drive the borrowing headroom, the dimensions or the route.

Who may change them, until the agreement is closed or cancelled:

- the borrower may add rows at any time, but remove only the rows they added,
  and only while the request is a draft;
- unit finance (`group_advance_payment_user`) and the loan officer may add and
  remove any row.

Every addition and removal is logged on the agreement. An endorser only reads.

`agx_related_document_sarabun` seeds the หนังสือสารบรรณ kind.
