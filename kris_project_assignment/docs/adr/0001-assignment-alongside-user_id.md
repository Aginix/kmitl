# `assigned_to` alongside `user_id` on `kris.project`

`kris.project` already has `user_id` (`res.users`, string "Responsible") — the KRIS
Officer who owns the record. `assignment.mixin` from `base_assignment` requires a field
called `assigned_to`. This add-on introduces `assigned_to` as a **separate field**
rather than renaming `user_id`.

## Two roles, not one

- `user_id` — the _fixed_ owner. Set at create (defaults to the creating user) and
  rarely changes; drives per-user record rules and the "My Project" filter that already
  exists in `kris_project`.
- `assigned_to` — the _current handler_. A rotating role: an officer may claim an
  unassigned project (Assign to me), a manager may reassign or unassign (Assign… /
  Unassign). The associated `mail.activity` acts as a Todo-inbox reminder for the
  assignee.

These are two distinct concepts. A project owned (created) by Officer A may be
_currently handled_ by Officer B during a specific phase without Officer A losing
ownership. Collapsing both into one field would remove that distinction.

## Why not rename `user_id`

- Odoo convention treats `user_id` as the "responsible / owner" field across many core
  models (`sale.order`, `purchase.order`, `mrp.production`, `project.project` — every
  one keeps `user_id` for the owner and layers a separate concept for the current
  actor).
- CONTEXT.md already documents `user_id` as "the owning KRIS Officer", and the search
  view exposes a `my_projects` filter (`user_id = uid`) users are familiar with.
- Renaming an existing column with data in it needs a pre-migration and breaks any
  downstream module that references `kris.project.user_id`.
- The precedent set by `disbursement_assignment` (which added `assigned_to` alongside
  disbursement.request's existing `user_id` for the creator) is the same shape.

## Why not skip `user_id` entirely

Removing `user_id` would break `my_projects` (users see it in daily use), existing
record-rule scopes, and any external report that groups by "responsible". The cost of
keeping both fields is a small amount of duplication in the form ("Responsible" and
"Assigned Officer" appearing next to each other); the cost of removing `user_id` is
measurable regression across the module.

## Guarantee

The two fields never diverge silently: assignment lifecycle events fire through the
mixin's public API (`action_assignment_*`, wizard) and update only `assigned_to`.
`user_id` continues to be written the way it always was.
