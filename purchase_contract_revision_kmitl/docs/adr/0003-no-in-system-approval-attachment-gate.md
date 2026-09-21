# 0003 — No in-system approval; use an attachment-file gate instead

Status: accepted (2026-09)

## Context & Decision

The initial design proposed integrating contract amendment approval through
e-Saraban (mirroring the `advance_payment` #1238 approach with
``sarabun.document.mixin``). Late in the grill session the user reversed
this: at KMITL, approval of a contract amendment happens **outside the ERP** —
the officer receives a paper approval memo / สารบรรณ record, then records the
change in the ERP after the fact.

The system therefore does **no** approval routing. It only gates
``action_apply`` on the presence of at least one attached file in
``approval_attachment_ids`` (M2M ``ir.attachment``). No file → UserError.

## Why

- Matches the real workflow. Building an e-Saraban cycle would duplicate what
  the paper track already does and force officers to re-submit approvals they
  already have.
- Keeps the model surface small — no ``to_approve`` / ``returned`` / ``rejected``
  states, no callbacks from ``sarabun.document.mixin``, no route template
  configuration burden.
- The attachment is the **evidence**, not the authorisation. Someone reading
  a historical revision can open the attached memo and see who authorised it.
- Deliberately weaker than the earlier proposal — accepting that this makes
  it easier to record a "revision without evidence" if the officer somehow
  attaches an unrelated file. That trade-off was explicitly made; it's a
  design decision, not an oversight.

## Consequences

- ``purchase.contract.state`` has only three values (``draft``, ``applied``,
  ``cancelled``) — the four extra approval states from the earlier draft are
  removed.
- Manifest depends on standard ``ir.attachment`` / ``mail.thread`` only —
  no ``agx_sarabun`` dependency.
- **No metadata validation.** We don't require the attachment to carry a
  memo number, date, or signer field. If the audit team later asks for these
  structured fields, add them as required Char/Date/Many2one on
  ``purchase.contract`` — this is the natural extension point.
- Chatter (``mail.thread``) on the contract provides the audit trail:
  ``action_apply`` posts a message noting the applying user and timestamp;
  ``action_cancel`` does the same for cancellation.
- Anyone reading this code who expects the ``sarabun.document.mixin``
  pattern (because it's used elsewhere in the codebase — advance_payment,
  purchase_request) will find its absence surprising. Point them at this
  ADR.

## Open items

- The user hinted at possibly adding attachment metadata later (memo number
  / date / approver). Left out of scope for the initial cut; add as required
  fields on ``purchase.contract`` if requested.
