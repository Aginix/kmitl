=========================
KMITL Accounting Tracking
=========================

Maximises chatter tracking on Journal Entries / Invoices (``account.move``)
using the OCA `tracking_manager` module — no custom Python.

What it does
============

* Turns on ``tracking_manager`` custom tracking for ``account.move`` and marks
  the header/amount/technical fields to track (in addition to the fields Odoo
  core already tracks natively). Scalar and many2one changes appear as standard
  chatter tracking values.

* Marks the ``invoice_line_ids`` one2many so that adding, changing or removing a
  business line (product / section / note line — i.e. every line of a plain
  journal entry, and the product lines of an invoice) is summarised as a note on
  the move chatter. ``account.move.line`` is scoped to a curated field list so
  the note is not noisy; auto-generated tax / receivable / payment-term lines
  (``line_ids`` only) are deliberately not tracked.

How it works
============

Everything is configuration data — a single ``noupdate="1"`` file
(``data/account_move_tracking_data.xml``) sets ``active_custom_tracking`` on the
``ir.model`` records and ``custom_tracking`` on the ``ir.model.fields`` records,
exactly like ``kris_project`` does for its own models. Because the records are
``noupdate``, administrators can re-tune the tracked fields from
*Settings > Technical > Database Structure > Models* without a module upgrade
resetting their choices.

Localisation
============

Field names in the chatter are already translated by the ``account`` / ``base``
Thai catalogs. The structural verbs of ``tracking_manager``'s line-change note
(``New`` / ``Delete`` / ``Change``) are translated to Thai in
``i18n/th.po``.
