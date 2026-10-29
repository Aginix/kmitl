====================================
Disbursement — Sent Back Exception
====================================

A request the officer sends back to its maker (ส่งคืนผู้จัดทำ, back to draft)
shows the non-blocking exception *ส่งคืนผู้จัดทำ* in ข้อผิดพลาด — on the form and
in the list — until the maker resubmits it.

The rule is a marker: the send-back links it and the next state change clears
it; exception detection never evaluates it. Other modules add markers of their
own through ``_sent_back_rules`` (e.g. ``disbursement_change_request``). A
request returned to its source document stays in the circuit and is not marked.
