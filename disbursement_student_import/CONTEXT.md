# Disbursement — Student List Import

Bringing a long list of students — a scholarship round, a semester's teaching-assistant
pay — onto a draft **Disbursement Request** from one Excel file, instead of picking each
**Payee** by hand. Every line it adds is an ordinary request line; nothing downstream
knows it was imported.

## Language

**Student list import** (นำเข้ารายชื่อนักศึกษา):
Adding one request line per row of the requester's Excel file — student ID, amount,
bank account, optional national ID and description — to a draft request whose
**Payee type** is นักศึกษา, all under the one expense item chosen for the import. It
only ever appends; the request's existing lines are left alone.
_Avoid_: Upload, Sync, Bulk create.

**Import template** (แบบฟอร์มนำเข้า):
The Excel file the import reads, downloaded from the import itself, with its columns in
a fixed order and the bank picked from a list.
_Avoid_: Format, Sample file.

**Ready row** (แถวพร้อมนำเข้า):
A row that resolves to a **Student** (see `partner_student_kmitl`) and to a bank
account — its own, or the one the student already has. Only ready rows become lines.
A ready row may still carry a **warning**.
_Avoid_: Valid row.

**Skipped row** (แถวที่ข้าม):
A row that cannot become a line — its student ID is on no contact and not in the
**Student catalog** (or the catalog is not connected), it has no amount, or the student
has no bank account at all. Listed in the preview and in
the note left on the request; never blocks the ready rows.
_Avoid_: Error row, Rejected row.

**Warning** (คำเตือน):
Something on a ready row the requester should look at but that does not stop it: the
same student appearing twice (a TA paid for two courses is legitimate), a national ID
that differs from the one on record, or a taxable request with no national ID.
_Avoid_: Error (an error stops the import).
