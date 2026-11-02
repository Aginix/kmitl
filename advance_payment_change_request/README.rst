=====================================
Advance Payment - Change Requests
=====================================

สัญญายืมเงิน takes Change requests (ข้อแก้ไข, ``agx_change_request``): whoever
checks the request details what the borrower must fix or explain.

* Besides the author, whoever may send the request back at its step may close
  one on the author's behalf: the supervisor at ``to_endorse``, the director at
  ``to_director``, the assigned loan officer at ``to_verify``.
* **ยังมีข้อแก้ไขที่ค้างอยู่** (blocking, switchable): Verify is refused while
  a request is open or answered. No other step waits.
* A ส่งกลับแก้ไข while requests are outstanding lists them in the chatter and
  flags the loan **มีข้อแก้ไขที่ต้องแก้** next to ส่งกลับแก้ไข.

Deployment
==========

``-i advance_payment_change_request`` (not auto-installed).
