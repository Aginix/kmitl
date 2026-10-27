=====================
Disbursement Stations
=====================

Routes the disbursement request (ใบขอเบิก) through **stations** (สถานี): the desks a
request passes through between the head's signature and the payment. It plugs the
request into the station engine of ``work_center``; see ``CONTEXT.md`` for the terms and
``work_center/docs/adr/`` for the engine.

What entering the circuit means
===============================

* Signing the request (``action_sign``, including the e-Saraban completion) puts it
  ``in_progress`` at the **first station of the route**, and every move after that is
  written to the visit log (สมุดเยี่ยม). A request the maker corrected and resubmitted
  re-enters at the first station without a new head signature.
* Forwarding out of the last station makes the request ``done``. That says nothing about
  the money, which the settlement stage (ขั้นการชำระ) follows on its own.
* Sending back (the Return wizard), resetting to draft and cancelling take the request
  out of the circuit. Inside it only the people responsible at the station holding the
  request may do so; there is no manager override. A ``done`` request cannot be reset.
* With no active route the request stays ``signed`` and a warning is logged. The route
  is seeded **active**, so a request signed after install enters the first station at
  once: configure the stations (below) right after installing. Requests signed before
  the install stay ``signed``; select them and run *Action > Send to Stations*
  (officers) to put them at the first station.

Configuration
=============

The module seeds the work area, six central stations (หมวดตรวจ, ผอ.กองคลัง,
ผู้รับมอบอำนาจอธิการบดี, ตั้งหนี้, ตรวจจ่าย, อนุมัติจ่าย), the route over them and a
counter. **The seeded stations start with neither acts nor members**: the "an act or a
member" rule is only skipped while the data loads. An administrator then lists on each
station the acts it allows and requires, the parts of the request it lets people edit,
and its members (Settings > Stations). Until a station has members, every holder of the
roles of its acts is responsible there.

The acts come from the modules that implement them (``disbursement_validation``,
``disbursement_approver_director``, ``disbursement_approver_rector``,
``disbursement_budget``, ``disbursement_accounting_kmitl``,
``disbursement_finance_kmitl``) and are reflected into the station configuration after
every install or upgrade. The five editable parts (header, lines, attachments,
dimensions, budget) are declared here, for the officer role.

What is deliberately not enforced
=================================

* **Order.** Acts are not ordered against the request's state: a station may allow any
  act, forwarding without a required act only needs a reason, and the reason is logged.
  Only integrity checks remain (an act is never done on a draft or a cancelled request).
* **Editing is a screen lock, not a security rule.** A part is editable when the station
  holding the request lists it and the money has not started. Two things narrow it
  further, on purpose: a draft bill locks the lines, dimensions and budget, and a
  budget commitment locks the dimensions and the budget.

Installing
==========

Install ``work_center`` and this module (``-i disbursement_work_center``). Install it
with ``disbursement_validation_assignment`` in place of ``disbursement_assignment_kmitl``:
the old module's assign buttons and backlog only look at ``signed`` requests, which a
routed request leaves at once. Requests that were already ``signed`` stay ``signed``
until they are sent to the stations (above); there is no migration.
