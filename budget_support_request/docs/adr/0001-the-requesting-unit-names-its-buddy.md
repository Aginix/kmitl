# The requesting unit names the Buddy who will handle its request

A budget support request carries **one** central-office **Buddy** (`officer_id`), named by
the **requesting unit** when it files the request and pre-filled from the shared
`budget_buddy` coverage settings. That one person — nobody else — gets the Todo to fulfil
the request once it is approved. There is **no separate "support officer" role**: the Buddy
role already in use across Budget is reused as-is, coverage settings and all.

## Why

Central staff at KMITL already hold all-OU access, so "who is allowed to see this request"
was never the problem. The problem is **who is expected to act on it**. The first design
pinged every member of a dedicated notify-only group, which produces a Todo per officer for
every approved request and leaves responsibility diffuse: everyone is told, nobody is named,
and the requesting unit has nobody to chase.

Reusing Buddy rather than minting a second central-officer role also removes a genuine
ambiguity. A unit's Buddy and its "support officer" would have been the same people in
practice, maintained in two places, drifting apart the first time someone is added to one
and not the other.

Letting the **unit** name the Buddy — rather than central assigning one on approval — is the
part most likely to surprise a reader. It follows from where the approval actually happens:
the live path routes the request through e-Saraban, and when the letter completes, approval
fires from the engine's callback. There is no moment in that path where a Budget Manager is
holding the record and could be asked to assign someone. Pushing the choice to filing time
is the only placement that does not leave a hole, and it matches how the unit already works:
it knows which Buddy looks after it and deals with them directly. The coverage settings
pre-fill the answer, so in the normal case the unit confirms rather than decides.

An assignable Buddy is filtered to those whose record rules actually let them read the
request — a Buddy who could not open the Todo is never offered.

## Considered Options

- **Notify the whole group, first to act claims it** — rejected: the repo's Todo layer does
  support claiming, but it makes every approved request land in every central officer's
  inbox until someone acts, which is the inbox-flooding problem that
  `mail_activity_todo` ADR-0007 exists to avoid. It also defers responsibility past the
  point where the unit might need to chase someone.
- **Central assigns the Buddy at approval** — rejected: the e-Saraban path has no such
  moment (see above), so the field would be empty exactly when it is needed.
- **Keep a `group_budget_support_officer` and default its members from Buddy coverage** —
  rejected: two roles for one job, maintained separately.

## Consequences

- `budget_support_request` depends on `budget_buddy`. Coverage rows are keyed on
  `budget.support.request` as a model, so a unit's Buddy for support requests can be
  configured independently of their Buddy for transfers — same mechanism, separate rows.
- Naming a Buddy is part of filing: submission is refused without one, with a message that
  says the unit has no covering Buddy configured rather than a bare required-field error.
- Changing the request's unit or amount in draft re-defaults the Buddy, but a Buddy the
  settings still assign is kept — editing a draft never silently undoes the unit's pick.
- Approval schedules exactly one `mail.activity`, so "approved but nobody picked it up" is
  visible as one person's overdue Todo instead of being spread across a group.
- A Buddy is a `budget.group_budget_user`, so no extra ACL row is needed for them to read
  the request.
