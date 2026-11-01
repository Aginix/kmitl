==========================================
KMITL Budget Transfer — Change Requests
==========================================

Budget transfers take Change requests (``agx_change_request``) on top of Buddy
Verification (``budget_transfer_verify``); see *Buddy Verification* in
``budget/CONTEXT.md``.

* The Buddy details what to fix as Change requests, on the transfer or pinned
  on its files.
* **ยืนยันตรวจสอบ** is refused while any request is outstanding (open or
  answered), whoever made it, with ``budget_transfer_exception_change_request``
  (an exception rule an administrator may switch off).
* **ส่งกลับแก้ไข** needs no reason while requests are outstanding: the wizard
  lists them, and so do the note and the requester's correction To-Do.
* A Buddy covering the transfer may close a request on its author's behalf.
