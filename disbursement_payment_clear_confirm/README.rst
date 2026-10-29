===========================================
Disbursement Payment Clearing Confirmation
===========================================

The accounting officer (ยืนยันล้างหนี้) confirms that every payment of a disbursement
request is booked: every payee is paid and every live voucher's entry is posted, which
is what clears the bills it paid. The press posts nothing: each entry is posted through
the account.move maker-checker. It names the entries still to post.

The act code ``disbursement.confirm_cleared`` is the one stations list as allowed or
required (see ``disbursement/CONTEXT.md`` for the terms). The act changes no state: it
stamps ``clear_confirmer_id`` / ``clear_confirm_date`` and leaves one ``payment_clear``
signature row. A reset to draft clears both, and so does anything that takes the
request's payment back out of booked (an entry reset or cancelled, a cheque bounced).

Configuration
=============

Stations are administrator data: after installing, open Disbursement → Stations, add
the station where the accounting office books the payments (after the paying station)
to the route, and add *Confirm Cleared* to its Allowed Acts, and to its Required Acts
to keep the request there until the clearing is confirmed.
