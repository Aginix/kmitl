# พจ.1 (PA) carries its own Assigned Officer, independent of พ.1 (PR)

We give `purchase.request.approval` its own **Assigned Officer**, stored in `pa_assigned_to`, and
show a banner + "Assign to me / Assign… / Unassign" buttons on the PA form — matching the PR
experience. PA's officer is **not derived from and never mirrored to** the parent PR: creating a PA
leaves `pa_assigned_to` empty, unassigning on PA does not touch the PR, and the two can be
different people for the lifetime of the documents.

This supersedes the "PA has no officer of its own" clause of ADR-0001.

## Why the reversal

The original ADR-0001 argued that duplicating the officer onto PA "invites drift" and that PA can
just derive from PR. In practice, drift is what the domain actually wants: the PA is a *new stage
of work* (ขออนุมัติจัดซื้อ) that is typically picked up by a new officer once the PR has been
approved and handed off to procurement. Forcing PA to reflect PR's officer:

- Hid the fact that a different person now owned the work, so no one could tell from the PA who
  was actually handling it.
- Broke "Assigned to me" filtering on PA — officers who took over at the PA stage never appeared
  as assignees; officers who had finished at the PR stage still did.
- Blocked the natural "claim your work" UX at the point where procurement officers spend most of
  their time (opening PAs, not PRs).

The concern that drift would confuse users is addressed by keeping the PR's officer visible on PA
(as `pr_assigned_to`, a related field shown in the tree and search view alongside `pa_assigned_to`)
so both stages are legible at a glance.

## Considered options

- **Rename PA's `assigned_to` (Approver) to `approver_id`** to free the `assigned_to` name for the
  officer, matching PR/PO. Rejected: churns the working approval code paths, needs data migration
  in downstream modules that reference the field, and gains only naming symmetry.
- **Backfill `pa_assigned_to` from `request_id.assigned_to` at install time** so existing PAs are
  not all "unassigned" after upgrade. Rejected: contradicts the mental model that PA's officer is
  a fresh claim by the person actually doing PA-stage work, and would silently carry stale PR
  officers into PA "My Work" lists.

## Consequences

- **Mixin is parameterized by field name.** `AssignedOfficerMixin` gained `_assign_field`
  (default `"assigned_to"`); PA overrides it to `"pa_assigned_to"`. The mixin's `@api.depends`
  moved off the mixin to each consumer's own compute override, since decorators need the concrete
  field name.
- **`assign.officer.wizard` uses the mixin's accessor** (`record._assignment_get_officer()`
  / `record._assignment_set_officer(user)`) instead of hardcoded `record.assigned_to`.
- **Search view on PA has two "Assigned to me" filters** — one per document — so users can pick
  the perspective they care about. The "Unassigned" filter targets `pa_assigned_to` (matching
  what the banner is telling them).
- **No migration ships with this change.** Existing PAs land with `pa_assigned_to = False`; the
  yellow banner acts as a visible signal to the team that a new field is available. Users claim
  active PAs with a single click.
- **PR and PA officers can permanently diverge.** This is by design; the PR's officer remains
  visible on the PA form and tree so coordination between stages is not lost.
