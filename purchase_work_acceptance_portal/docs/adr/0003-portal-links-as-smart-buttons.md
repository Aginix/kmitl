# Portal + PO links live as smart buttons on the WA backend form

The committee review Todo ([ADR-0001](./0001-committee-notification-via-mail-activity-todo.md))
is a `mail.activity` whose primary "Open Source" button opens the WA backend
form ([mail_activity_todo ADR-0001](../../../mail_activity_todo/docs/adr/0001-todos-are-native-mail-activity.md)).
The committee member still finishes the review from a **portal** page with
their own `committee_token`, and often needs the PO portal page too. We put
both URLs as **smart buttons** in the WA form's `oe_button_box`, computed
live from `env.user` when clicked. The Todo card stays clean — summary,
note, deadline, primary "Open Source" — and the smart buttons are the
natural place to jump to portal from once the form is open.

The committee-portal button reads `is_current_user_committee` (a computed,
non-stored, `depends_context=("uid",)` field) to stay invisible for users
who are not on the committee — its URL only works with a matching
`committee_token`. The PO-portal button mirrors the existing "Purchase
Order" smart button's visibility (`purchase_id` set): PO portal is gated by
the WA's own `wa_token`, no per-user token in play, so everybody who can see
the WA can open it.

## Why

- **The Todo card should stay compact.** Two extra pills per row is noise
  in a scan-heavy inbox — users compare and prioritise there, they don't
  act. The backend form is where they act.
- **One entry point per Todo.** ADR-0001 of `mail_activity_todo` makes the
  primary "Open Source" button load-bearing. Adding a second entry point on
  the Todo card weakens that; putting the portal links behind "Open Source"
  keeps that invariant unambiguous.
- **`env.user` is trivially available on a click.** No need to resolve
  per-viewer tokens at `get_my_todos()` time, no need for an OWL template
  extension. The click handler already has full server context.
- **A committee-invisible button beats a click-then-error button.** Smart
  buttons are always visible unless attrs-hidden; showing "ตรวจรับใน
  Portal" to a non-committee and then raising `UserError` on click reads
  as broken. `is_current_user_committee` gates the button off entirely.

## Considered options

- **Keep the action-link pills on Todo cards (former ADR-0002, superseded and removed).**
  Committee sees the URL directly from the inbox — but pills required
  extending `mail_activity_todo_discuss`'s OWL template, overriding
  `get_my_todos()` to resolve per-viewer tokens, and a bespoke hook on
  `mail.activity`. All that infrastructure now supports zero features.
  **Superseded by this ADR.**
- **A single "Open in Portal" button that server-side decides which URL
  fits.** Ambiguous — a committee member wants portal-WA more than PO,
  a non-committee looking at the WA might want PO — one button cannot
  encode that intent. **Rejected.**
- **Menu items or breadcrumb links instead of smart buttons.** Discoverability
  is worse; users on this form scan the button box for actions. **Rejected.**

## Consequences

- Two smart buttons on the WA form:
  - `action_open_committee_portal` — visible when
    `is_current_user_committee=True`; returns `ir.actions.act_url` with
    `target="new"` carrying the current committee row's `access_token` as
    `committee_token`.
  - `action_open_purchase_portal` — visible when `purchase_id` is set;
    returns `ir.actions.act_url` with `target="new"` carrying the WA's own
    `access_token` as `wa_token`.
- The Todo card shows no portal URLs. Committee clicks "Open Source" (which
  lands on the WA form) and then clicks a smart button. One extra click
  compared to the pills; the trade for a clean inbox and no OWL extension.
- ADR-0002 (portal links on review Todo) is superseded and removed. With
  it goes: `mail.activity._get_todo_action_links` on this module,
  `res.users.get_my_todos` override, the OWL template extension, the
  `mail_activity_todo_discuss` dependency, and the `assets` block in the
  manifest.
- `is_current_user_committee` is computed and non-stored — no DB column,
  no indexes. It re-evaluates whenever the form renders because it depends
  on `uid` context, so it stays correct across users without a compute-on-
  read pitfall.
- **Sudo is required for token generation and cross-OU PO reads.**
  `_portal_ensure_token()` writes `access_token`; committee users hold
  read on the WA and committee row but usually not write. The linked PO
  is also frequently behind an operating-unit rule the committee is not
  in. Both smart buttons `sudo()` the affected records only where they
  must — the URL itself is portal-gated by tokens, so no privileged data
  leaves the server.
