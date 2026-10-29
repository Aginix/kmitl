=====================================
Disbursement Bill Posted Confirmation
=====================================

The accounting officer (ตั้งหนี้) confirms that every bill of a disbursement request is
posted. The press checks each live bill (``bill_ids``, cancelled ones aside) and names
those still to post, so a request never leaves the billing station for the payment
audit with a bill pending.

The act code ``disbursement.confirm_bill`` is the one stations list as allowed or
required (see ``disbursement/CONTEXT.md`` for the terms). The act changes no state: it
stamps ``bill_confirmer_id`` / ``bill_confirm_date`` and leaves one ``bill_confirm``
signature row. A reset to draft clears both, and so does a posted bill reset to draft
or cancelled.

Configuration
=============

Stations are administrator data: after installing, open Disbursement → Stations →
Billing and add *Confirm Bills Posted* to its Allowed Acts, and to its Required Acts
to keep the request at the station until the bills are confirmed.
