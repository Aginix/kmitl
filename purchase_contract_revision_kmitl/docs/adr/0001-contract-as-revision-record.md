# 0001 — Contract as a revision record (N per PO), not a container with revision children

Status: accepted (2026-09)

## Context & Decision

The PO amendment redesign needed a data model that supports full history +
reprint of any historical version. Two shapes were considered:

- **A (chosen)**: ``purchase.contract`` is the *revision record*. One PO owns
  N contract records, one per revision. Rev 0 is auto-created at PO confirm;
  subsequent revs are user-initiated. The PO carries a computed
  ``current_contract_id`` M2O pointing at the latest applied revision.
- **B (rejected)**: ``purchase.contract`` is a single container per PO
  holding "current" state, with a separate ``purchase.contract.revision``
  child model holding historical snapshots.

We chose A.

## Why

- Matches the requirement's own phrasing — "revision **เก็บไว้ที่** Contract"
  (revisions **stored at** Contract) — reading Contract as the storage bin,
  not as a container that holds revisions.
- One less model. Option B needs three (PO + Contract + Revision) to express
  what A does with two.
- Each ``purchase.contract`` record is complete: it holds a full snapshot of
  header + lines + งวด + committees. Printing "revision 3" is a straight
  render of one record; option B would require joining Contract + Revision-3.
- Historical query is a plain search on ``purchase.contract`` filtered by
  ``purchase_id`` and ``revision_number`` — no drill-down through a container.
- The "which revision is authoritative" answer that B gives cheaply (the
  container is the answer) is available in A at the same cost via
  ``current_contract_id`` — a stored computed field.

## Consequences

- ``purchase.order`` doesn't own contract fields directly; it reads them
  through ``current_contract_id``. The physical fields (``fines_rate``,
  ``supervision_cost`` etc.) still exist on ``purchase.order`` — synced
  written from the revision on ``action_apply`` — so existing modules that
  read them keep working.
- Rev 0 exists for every confirmed PO. The ``button_confirm`` override
  creates it; the ``migrations/16.0.1.0.0/post-migration.py`` script
  backfills for existing POs.
- The concurrency invariant (one draft per PO) is enforced via a Python
  ``@api.constrains`` on the contract, not via container semantics.
- **Committee sync is deferred** (open item — see CONTEXT.md).
- **The old ``purchase_order_change`` and ``purchase_order_change_committee``
  modules are deleted** as part of this cutover. Deployments must uninstall
  those modules through the Apps UI before this module goes on top.
