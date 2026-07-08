# Assigned Officer is modeled on `assigned_to`; PA derives it from its parent PR

We give each procurement document one **Assigned Officer** (เจ้าหน้าที่ผู้รับผิดชอบ) so officers can
find their own work. We store it on the existing `assigned_to` field — repurposing PR's hidden OCA
"Purchase Representative" and adding a same-named field to PO — so the concept and the "My Work"
filter are uniform across documents.

**PA stores no officer of its own.** A `purchase.request.approval` always belongs to exactly one
`purchase.request`, so duplicating the officer onto PA would invite drift. PA's officer is
`request_id.assigned_to`, and PA's own `assigned_to` keeps its existing, distinct meaning (Approver).
Hence PA has no assign buttons; its "My Approvals" list filters on `request_id.assigned_to`.

## Considered options

- **A new dedicated `assigned_officer_id` field** — clearer name, but leaves PR's OCA `assigned_to`
  permanently dead and introduces a third user concept alongside `user_id` and `assigned_to`.
- **Renaming PA's Approver field to free up `assigned_to`** — churns working approval code and needs
  a data migration, for no real gain since PA can derive the officer from its PR.

## Consequences

- The assignment behavior (buttons, manager/user gating, assign wizard, "To Do" activity lifecycle,
  take-over toggle) is built **concretely** on `purchase.request` and `purchase.order` for now. The
  logic is kept centralized so it can be lifted into a reusable `assignment.mixin` (parameterized by
  per-model user/manager group hooks) when a second, non-purchase consumer appears — deferred, not designed in.
- No dedicated "My Work" landing menu ships here. Officers find their work via the per-document
  "Assigned to me" filter; the landing/todo experience is deferred to a future generic
  `mail_activity_todo` app.
