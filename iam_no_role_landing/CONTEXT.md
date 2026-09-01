# No-Role Landing

A UX gate that intercepts backend users who have not yet been assigned a role,
shows them a friendly landing page, and prevents them from seeing a broken
empty UI or raw Odoo AccessError pages. This module does not add data-level
security — Odoo's existing group ACL and record rules remain the real guard.

## Language

**Gated user**:
An internal `res.users` whose `role_line_ids` is empty and who does not hold
`base.group_erp_manager`. Every backend URL is redirected to the No-Role
Landing until an IAM Manager assigns at least one role.
_Avoid_: inactive user, suspended user, locked user (those imply `active=False`
or a password lock — a gated user is fully active, just unconfigured).

**No-Role Landing**:
The client action (`ir.actions.client` tag `iam_no_role_landing.landing`) shown
to gated users. Displays the Contact Message and two buttons: **ตรวจสอบสิทธิ์**
and **ออกจากระบบ**.
_Avoid_: error page, access-denied page (the landing is deliberate onboarding
UX, not an error state).

**Contact Message**:
A plain-text string stored in `ir.config_parameter`
`iam_no_role_landing.contact_message` and rendered on the landing.
Editable by anyone with `base.group_erp_manager` via Settings ▸ Technical ▸
Parameters ▸ System Parameters.
_Avoid_: admin email, contact info (the message may contain any text the IAM
Manager chooses — name, email, phone, instructions).

**Exempt user**:
Anyone with `base.group_erp_manager` or above (which includes
`iam.group_iam_manager`, `base.group_system`, and the superuser). Never gated
regardless of `role_line_ids`, so bootstrap and role remediation always work.
_Avoid_: admin user (too narrow — any erp_manager-level user is exempt, not
just the system administrator).

**ตรวจสอบสิทธิ์ (Re-check)**:
The button on the landing that calls `res.users.check_role_status()`. If the
gating condition has cleared (an IAM Manager assigned a role while the browser
was open), performs a hard reload to `/web` so the session group cache and
menus are refreshed. If still gated, shows a notification.
_Avoid_: refresh, reload (the button does a hard reload only when the role is
confirmed — otherwise it stays on the landing).

See also: [[iam]] (the delegated-admin app that manages roles and groups).
