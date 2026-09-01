# Standalone page + HTTP dispatch gate, exempt base.group_system

A gated user (no roles) has no `base.group_user` (because `base_user_role`
clears `groups_id` when `role_line_ids` is empty), so the Odoo webclient
cannot load — every field read, menu load, and action fetch returns Forbidden.
A client action inside the webclient is therefore unusable for this audience.

We serve a **standalone HTTP page** at `/iam/no-role` using `web.login_layout`
(the same base as the login and password-reset pages), which requires only a
valid session — no group permissions. The `ir.http._pre_dispatch` hook
redirects every non-whitelisted, non-JSON-RPC backend request from a gated
user to this page. The whitelist covers logout, static assets, the landing
itself, and the `/iam/check-role` JSON endpoint.

`_is_role_gated()` uses `sudo()` to read `role_line_ids` because the gated
user's own ACL cannot access the field.

Exempt threshold is `base.group_system` (full Settings access). Only system
administrators can bypass the gate without a role. IAM Managers and
`base.group_erp_manager` holders are **not** exempt — they must have at least
one role assigned to enter the backend. The system admin is responsible for
bootstrapping IAM Managers with a role.

**Considered options rejected:**
- *Client action in webclient* — webclient cannot load for a user with no
  groups; every request returns Forbidden before the landing renders.
- *Exempt `base.group_erp_manager`* — too wide; many internal users may hold
  `erp_manager` through role implication without being administrators.
- *Intercept JSON-RPC* — breaks the landing's own `/iam/check-role` call and
  every Odoo subsystem that issues RPC on page load.
