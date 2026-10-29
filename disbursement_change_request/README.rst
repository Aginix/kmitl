=====================================
Disbursement — Change Requests
=====================================

Disbursement requests take Change requests (``agx_change_request``): the officer
details what to fix as Change requests, on the request or pinned on its files.

* **ตรวจสอบ** (``action_validate``) is refused while any request is outstanding
  (open or answered), whoever made it, with
  ``excep_disbursement_outstanding_change_requests`` (an exception rule an
  administrator may switch off).
* **ส่งกลับแก้ไข** needs no reason while requests are outstanding: the wizard
  lists them, and so do the note and the requester's correction To-Do.
* Whoever may send the request back (the people at the station holding it, or a
  disbursement officer before it reaches a station) may close a request on its
  author's behalf.
