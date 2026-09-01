# No-Role Landing

A UX gate that intercepts backend users who have not yet been assigned a role,
shows them a wizard dialog, and prevents them from seeing a broken empty UI or
raw Odoo AccessError pages. This module does not add data-level security —
Odoo's existing group ACL and record rules remain the real guard.

## Language

**Gated user**:
An internal `res.users` whose `role_line_ids` is empty and who does not hold
`base.group_system`. Every backend URL is redirected to the No-Role Landing
until a system administrator assigns at least one role.
_Avoid_: inactive user, suspended user, locked user (those imply `active=False`
or a password lock — a gated user is fully active, just unconfigured).

**No-Role Landing**:
The wizard dialog (`ir.actions.client` tag `iam_no_role_landing.landing`) shown
to gated users. Displays the Contact Message and two buttons: **ตรวจสอบสิทธิ์**
and **ออกจากระบบ**.
_Avoid_: error page, access-denied page (the landing is deliberate onboarding
UX, not an error state).

**Contact Message**:
A plain-text string stored in `ir.config_parameter`
`iam_no_role_landing.contact_message` and rendered on the landing.
Editable by anyone with `base.group_system` via Settings ▸ Technical ▸
Parameters ▸ System Parameters.
_Avoid_: admin email, contact info (the message may contain any text the
administrator chooses — name, email, phone, instructions).

**Exempt user**:
Anyone with `base.group_system` (full Settings access) or the superuser. Never
gated regardless of `role_line_ids`, so bootstrap and role remediation always
work. Note that `iam.group_iam_manager` and `base.group_erp_manager` are
**not** exempt — they must have at least one role assigned or hold
`group_system` to bypass the gate.
_Avoid_: admin user (too vague — specifically the user must hold
`base.group_system`).

**ตรวจสอบสิทธิ์ (Re-check)**:
The button on the landing that calls `res.users.check_role_status()`. If the
gating condition has cleared (an administrator assigned a role while the browser
was open), performs a hard reload to `/web` so the session group cache and
menus are refreshed. If still gated, shows a notification.
_Avoid_: refresh, reload (the button does a hard reload only when the role is
confirmed — otherwise it stays on the landing).

See also: [[iam]] (the delegated-admin app that manages roles and groups).
