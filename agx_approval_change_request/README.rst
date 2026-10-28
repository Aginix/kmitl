=======================================
Aginix Approval — Change Requests
=======================================

Approval requests take Change requests (``agx_change_request``).

* ผู้ตรวจสอบคำขอ / ผู้ยืนยันงบประมาณ detail what to fix as Change requests, on
  the request or pinned on its files.
* **ยืนยันตรวจสอบ** is refused while any request is outstanding (open or
  answered), whoever made it: the exception rule *ยังมีข้อแก้ไขที่ค้างอยู่*,
  which an administrator may switch off or make non-blocking. It only holds
  while the request waits for verification.
* **ตีกลับ** needs no reason while requests are outstanding (open or
  answered): the wizard lists them, and so does the chatter note.
* A Request Verifier or Budget Confirmer may close a request on its author's
  behalf.
