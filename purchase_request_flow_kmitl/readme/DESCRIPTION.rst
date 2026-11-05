One cascade for every step back in the พ.1 → ก่อนสร้าง PO flow:

* ``_reset_to_draft``: ดึงกลับ (owner, any step up to sent), ตีกลับ (verifier /
  budget committer), หนังสือถูกตีกลับ, e-GP ยกเลิก — the request goes back to
  draft and its own ใบจองเงิน is released.
* ``_cancel_all``: ยกเลิก (draft only, owner) and ปฏิเสธ — cancels the พ.1, its
  พจ.1, their หนังสือ and the ใบจองเงิน. A signed หนังสือ keeps its state and gets
  a ยกเลิกผล note.
* พจ.1: draft keeps only สร้างหนังสือ / ส่งหนังสือใหม่ / ยกเลิก; ยกเลิก works from
  draft or straight from approved, blocked while a PO or other downstream
  document is live.
* Purchase settings: the user shown as creator of the auto-created พจ.1
  (default OdooBot).
