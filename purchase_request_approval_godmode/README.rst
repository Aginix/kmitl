====================================
Purchase Request Approval — God Mode
====================================

Elevated, narrow edit surface for พจ.1 (``purchase.request.approval``) in
the ``to_approve`` and ``approved`` states.

Members of the security group **Purchase Request Approval: God Mode**
(XML id ``purchase_request_approval_godmode.group_pa_godmode``) may edit
a limited set of PA fields without transitioning the record out of its
current state. This shortens the loop for real-world corrections
(vendor, tax, quantity, unit price, line description) that would
otherwise require cancelling and re-issuing the whole PA.

Unlockable fields
-----------------

Header (6):
  ``partner_id``, ``procurement_type_id``, ``procurement_method_id``,
  ``payment_type``, ``vat_included``, ``tax_id``.

Line (3) on ``purchase.request.approval.line``:
  ``product_qty``, ``price_unit``, ``name`` (ชื่อรายการ) — edit only.
  Adding/removing lines is not allowed; ``product_id`` and
  ``product_uom_id`` remain locked.

Everything else stays locked in God Mode: ``request_id``, ``name`` (PA
sequence), ``state``, ``title``, ``description``, ``assigned_to``,
``verified_by``, ``approved_by``, ``date_verified``, ``date_approved``,
``main_sarabun_document_id``, ``analytic_distribution``.

Budget cap rail
---------------

An ``@api.constrains`` on ``purchase.request.approval`` fires **only**
when the record is in ``to_approve`` or ``approved`` and the writing
user holds ``group_pa_godmode``. It enforces::

    sum(open PAs on the same budget_commitment_id) ≤ commitment.amount

Covering both single-PA and KMITL-Project shared-commitment cases.
"Open" means ``state in (to_approve, approved)``. If a correction needs
headroom the cap cannot supply, ops must raise the commitment cap first
(``budget.commitment._update_commitment_amount``); God Mode is not a
back door to cap growth.

Silent edits + PDF regeneration
-------------------------------

God-Mode ``write()`` calls run with ``tracking_disable=True``,
``mail_notrack=True``, ``mail_create_nolog=True`` — **no chatter entry,
no field-diff tracking, no follower notification** is emitted, for
either direct field edits or workflow buttons the god-mode user
presses.

When a god-mode edit touches a PDF-visible header field or the
``line_ids`` collection, ``_regenerate_report_pdf()`` unlinks the
stored ``<pa.name>.pdf`` ``ir.attachment`` and re-invokes the base
``report_generate()`` to produce a fresh one. This keeps the Sarabun
export/print flow in step with the corrected data (Sarabun's on-screen
preview was already live-rendering from QWeb; only the exported PDF
had gone stale).

Out of scope
------------

* Sarabun-side attachment lifecycle (owned by a separate branch which
  overrides ``write()`` on PA / PA line, diffs ``vals``, and updates
  the sarabun document's own PDF).
* Downstream PO / DR / bill re-derivation — God Mode is PA-only.
* Model-level ``write()`` guard for non-god-mode users (view-only
  rail, matching OCA convention).
* ``rejected`` / ``cancelled`` PAs — deliberately excluded from the
  God-Mode scope; edits there would confuse audit trails.

See ``docs/adr/0006-pa-godmode-edit.md`` for the full decision record.
