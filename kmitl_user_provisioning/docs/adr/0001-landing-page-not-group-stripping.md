# Gate un-provisioned users with a landing page, not group-stripping or UI interception

Internal users get created without an `hr.employee` link (manual creation, import, SSO). We want them unable to mess with business data, and to see a clear "contact admin" message rather than an empty home.

**Decision:** Detect the un-provisioned state *live* and only redirect the user's home action to a full-screen Provisioning Notice. We override `ir.http.session_info` to swap `home_action_id` when `res.users._is_provisioning_locked()` is true. We do **not** remove any group, and we do **not** intercept menu/app clicks.

The real protection is already there: every custom business app is gated by its own functional group, so a plain `base.group_user` account cannot see or reach them through the menu **or** a direct URL/RPC — the access layer denies it. The only gap a fresh account has is a confusing landing experience, which is all this module fixes.

The check is deliberately **soft**: a user stops being gated the moment HR links an employee *or* an admin grants any functional group. Because it is computed at `session_info` time, it needs no stored state, applies to already-existing accounts immediately, and self-heals on provisioning.

## Considered Options

- **Strip functional groups from un-provisioned users (enforce "no employee ⇒ no groups")** — rejected. It is destructive (the prior group set is lost and must be stashed/restored), needs `create`/`write` hooks on both `res.users` and `hr.employee`, and fights Odoo's group-keyed menu cache. It also blocks the legitimate "admin grants access before HR links the employee" workflow. Since native access control already denies app access to a group-less user, stripping adds risk without adding protection.
- **Demote to a share/portal user (remove `base.group_user`)** — rejected. Most airtight (no backend at all), but invasive: flips `user.share`, changes licensing/behaviour, the home-action mechanism no longer applies (share users are redirected out of `/web`), and provisioning must re-add `group_user`. Out of proportion for the goal.
- **Intercept menu/app clicks in JS and pop a "no permission" wizard** — rejected. This is the user's first instinct but it is UI-only: a determined user still reaches data via direct URL or RPC. It is security theatre over a real access boundary, and a client-side override to maintain.
- **Block at login** — rejected. The user should be able to log in and read the "contact admin" message (and self-heal once provisioned); a hard login block hides that.

## Consequences

- An un-provisioned user keeps `base.group_user`, so a few harmless standard apps (Contacts, Discuss, Calendar) remain reachable. Accepted: they carry no business data and the goal is protecting the custom apps, which are fully gated.
- "Provisioned" has two triggers — employee link **or** admin-granted functional group. The `_is_provisioning_locked` definition must keep both, or admin-override users would land on the notice while actually having app access.
- The baseline for "has a functional group" is `base.default_user`'s group set. If that template is ever configured with a functional group, *new* users would no longer be considered un-provisioned — keep `base.default_user` minimal (just `group_user`).
- `session_info` runs on every web-client bootstrap; the added check is a couple of `has_group` calls plus an `employee_ids` read — negligible, and only for logged-in sessions.
