====================================
Purchase Request Approval — God Mode
====================================

Elevated, narrow post-approval edit surface for พจ.1
(``purchase.request.approval``).

Members of the security group **Purchase Request Approval: God Mode
(post-approval edit)** (XML id
``purchase_request_approval_godmode.group_pa_godmode``) may edit a limited
set of PA fields while the record is in the ``approved`` state, without
transitioning it out of ``approved``. This shortens the loop for real-world
price / vendor / tax corrections that would otherwise require cancelling
and re-issuing the whole PA.

Unlockable fields
-----------------

Header (8):
  ``title``, ``description``, ``partner_id``, ``procurement_type_id``,
  ``procurement_method_id``, ``payment_type``, ``vat_included``, ``tax_id``.

Line (2) on ``purchase.request.approval.line``:
  ``product_qty``, ``price_unit`` (edit only — no add/remove; ``product_id``
  and ``product_uom_id`` remain locked).

Everything else stays locked (``request_id``, ``name``, ``state``,
``assigned_to``, ``verified_by``, ``approved_by``, ``date_verified``,
``date_approved``, ``main_sarabun_document_id``, ``analytic_distribution``).

Budget cap rail
---------------

An ``@api.constrains`` on ``purchase.request.approval`` fires **only** when
the record is in ``approved`` and the writing user holds
``group_pa_godmode``. It enforces::

    sum(approved PAs on the same budget_commitment_id) ≤ commitment.amount

Covering both single-PA and KMITL-Project shared-commitment cases. If a
correction needs headroom the cap cannot supply, ops must raise the
commitment cap first (``budget.commitment._update_commitment_amount``).

Out of scope
------------

* Sarabun sync of the edits (handled by a separate branch which overrides
  PA ``write()``; this addon just gives every unlockable field
  ``tracking=True`` so the sync side can detect changes cleanly).
* Downstream PO / DR / bill re-derivation (god-mode is PA-only).
* Model-level ``write()`` guard for non-god-mode users (view-only rail,
  matching OCA convention).

See ``docs/adr/0006-pa-godmode-edit.md`` for the full decision record.
