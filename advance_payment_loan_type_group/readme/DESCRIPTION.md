Adds **กลุ่มที่เลือกได้** to each loan type (ประเภทเงินยืม). A type that names
groups may be chosen, when drafting a loan, only by their members; a type that
names none stays open to everyone (advance_payment ADR-0031).

It limits who may *start* such a loan, not who may see one: the borrower,
endorser, director and approver still open it as usual.

On install, ค่าใช้จ่ายอื่นใด — the loan type with no source document — is
restricted to the loan officer (เจ้าหน้าที่งานเงินยืม), since borrowers must
otherwise borrow against a source (ADR-0029).
