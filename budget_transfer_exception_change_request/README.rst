==================================================
KMITL Budget Transfer Exception: Change Requests
==================================================

Adds the exception rule *ยังมีข้อแก้ไขที่ค้างอยู่* (``budget_transfer_exception``)
to budget transfers taking Change requests (``budget_transfer_change_request``):
**ยืนยันตรวจสอบ** is refused while any request is outstanding (open or
answered), whoever made it.

The rule only holds while the transfer waits for verification, so the
requester's ยืนยัน after a return goes through with the requests answered. An
administrator may switch it off or make it non-blocking under the exception
rules.
