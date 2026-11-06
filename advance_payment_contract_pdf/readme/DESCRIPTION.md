Adds a **พิมพ์สัญญา** button to the advance payment (สัญญายืมเงิน) form that
prints the official paper loan contract **สัญญาการยืมเงิน (แบบ สค.001)**
for hand signing.

- Page 1 is filled from the agreement: borrower, position, department,
  reason, amount (in figures and Thai words), contract number, due date,
  submission date and transfer date. Values not known yet print as
  dotted lines, so the form can be printed in any state, including
  draft.
- The signature blocks carry the signature image (from the employee's
  digitized signature) of each signer once they have acted: the
  borrower (ผู้ยืม) from submit, the supervisor (ผู้บังคับบัญชา, the
  เสนอ block) from เห็นชอบ, and the approver (คำอนุมัติ) from approval.
  Each block shows the signer's name (and position: the supervisor's job
  title; for the approver the fixed รองอธิการบดีฝ่ายการเงินและนิติการ
  ปฏิบัติการแทนอธิการบดี) and the date of the act. Until then, or after
  ดึงกลับ / ส่งกลับแก้ไข / cancel, the block is left blank for a hand
  signature. The borrower's ใบรับเงิน block is always signed and dated by
  hand; โอนเงินวันที่ is the Effective Date (วันที่เป็นลูกหนี้).
- The borrower paragraph (ข้าพเจ้า … / เพื่อเป็นค่าใช้จ่ายในการ …) is Thai
  distributed-justified: words are segmented with pythainlp so each line
  reaches the right margin without stretching only the few real spaces.
- Page 2 is the blank รายการส่งใช้เงินยืม ledger. It is a fixed PDF page
  that is appended after page 1 of every printed contract.
