=========================================
Attachment Logging - KMITL Extensions
=========================================

Extends OCA ``attachment_logging`` so that the × button on the
``many2many_binary`` widget actually deletes the ``ir.attachment`` (via the
mail delete endpoint) instead of just detaching it from the parent's m2m
relation. This closes two gaps in the stock behaviour:

* Deleted files no longer become orphan attachments consuming filestore
  space and remaining reachable through ``res_model``/``res_id`` queries.
* OCA ``attachment_logging`` fires its ``_delete_and_notify`` hook, so the
  audit note ("… unlinked a file: …") appears in the parent record's
  chatter — matching the behaviour of deletes done through the chatter
  paperclip.

Setup
=====

#. Install this module (depends on ``attachment_logging``).
#. Enable ``Settings → Discuss → Log attachment activity`` (system parameter
   ``attachment_logging.use_attachment_log``).

Scope
=====

Only the client-side ``Many2ManyBinaryField`` widget is patched. Chatter
uploads/deletes are already covered by OCA ``attachment_logging`` upstream
and remain unchanged. ORM-level ``create``/``unlink`` on ``ir.attachment``
(imports, scripts, wizards) is not covered and is out of scope for this
module.

Compatibility
=============

Coexists with other modules that patch ``Many2ManyBinaryField`` (e.g.
``agx_photoviewer``, ``web_attachment_document_type``) — each patch uses its
own scoped id so all overrides layer cleanly.
