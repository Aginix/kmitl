``base_assignment`` itself has no Settings UI. Each consumer owns its own
takeover toggle through the ``ir.config_parameter`` key returned by
``_assignment_takeover_param()``, and picks its own default with
``_assignment_takeover_default()``.

The toggle answers one question: **"When a document is already assigned to
someone, may another officer claim it via *Assign to me*?"**. When off,
takeover is a manager-only action (through *Assign…*). When on, any
officer in the user group can grab the document.

Reference implementations in this repository:

* ``procurement_assignment_kmitl`` — parameter
  ``procurement_assignment_kmitl.allow_takeover_assigned`` (default ``False``,
  conservative: manager-only reassignment). Exposed as a Settings toggle in
  the Purchase configuration page.

* ``disbursement`` — parameter ``disbursement.allow_takeover_assigned``
  (default ``True``, advisory: an officer may grab a mis-routed request out
  of the box).

Leave ``_assignment_takeover_param()`` returning ``None`` on your consumer
to drop the feature entirely — self-claim then works only on unassigned
records and any reassignment is manager-only.
