# Gate at both home-action and HTTP dispatch, exempt base.group_erp_manager

Overriding `_get_home_action` alone is not enough: a user who bookmarked
`/odoo/action-N` can bypass the landing and hit a blank Odoo AccessError
skeleton instead, which reads as "the app is broken" rather than "your account
is pending." We therefore also intercept at `ir.http._pre_dispatch` and
redirect any non-whitelisted, non-JSON-RPC request from a gated user back to
the landing action. The whitelist covers logout, static assets, and all
`application/json` requests (Odoo's own group ACL guards data there).

Exempt threshold is `base.group_erp_manager` (rather than just
`iam.group_iam_manager` or `base.group_system`) so that the full
erp-manager tier — which includes the IAM Manager — can always log in and
remediate a misconfigured role setup. A narrower exemption (system-only or
iam-manager-only) risked a deadlock where the person responsible for assigning
roles was themselves gated.

**Considered options rejected:**
- *Home action only* — bookmarked URLs bypass, user sees a broken skeleton.
- *Intercept all JSON-RPC* — breaks the landing's own ORM calls
  (`get_no_role_landing_info`, `check_role_status`) and every Odoo subsystem
  that issues RPC on page load.
- *`ir.rule` per model* — no single model to attach to; this is a route-level
  concern, not a record-level one.
- *Exempt system-only* — IAM Managers (the primary remediators) would be gated
  themselves if they had no role assigned, causing a bootstrap deadlock.
