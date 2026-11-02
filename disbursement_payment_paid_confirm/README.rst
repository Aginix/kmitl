=======================================
Disbursement Payment Paid Confirmation
=======================================

The finance officer (ยืนยันจ่ายสำเร็จ) confirms that every payee of a disbursement
request has been paid. The press pays nothing: each voucher is paid where its money
left, by closing the e-payment file that carried it, by handing the cheque over, or by
the cash press on the voucher. It checks that every payee has a live voucher and that
every live voucher is paid, and names those that are not.

The act code ``disbursement.confirm_paid`` is the one stations list as allowed or
required (see ``disbursement/CONTEXT.md`` for the terms). The act changes no state: it
stamps ``paid_confirmer_id`` / ``paid_confirm_date`` and leaves one ``payment_paid``
signature row. A reset to draft clears both, and so does anything that leaves a payee
unpaid again (a cheque bounced, a voucher cancelled or removed).

Configuration
=============

Stations are administrator data: after installing, open Disbursement → Stations, add
the station where the finance office pays (after Payment Authorization) to the route,
and add *Confirm Payment Completed* to its Allowed Acts, and to its Required Acts to
keep the request there until the payment is confirmed.
