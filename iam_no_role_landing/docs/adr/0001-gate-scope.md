# Gate at both home-action and HTTP dispatch, exempt base.group_system

Overriding `_get_home_action` alone is not enough: a user who bookmarked
`/odoo/action-N` can bypass the landing and hit a blank Odoo AccessError
skeleton instead, which reads as "the app is broken" rather than "your account
is pending." We therefore also intercept at `ir.http._pre_dispatch` and
redirect any non-whitelisted, non-JSON-RPC request from a gated user back to
the landing action. The whitelist covers logout, static assets, and all
`application/json` requests (Odoo's own group ACL guards data there).

Exempt threshold is `base.group_system` (full Settings access). Only system
administrators can bypass the gate without a role. IAM Managers
(`iam.group_iam_manager`) and `base.group_erp_manager` holders are **not**
exempt — they must have at least one role assigned to enter the backend.
The system admin is responsible for bootstrapping IAM Managers with a role.

**Considered options rejected:**
- *Home action only* — bookmarked URLs bypass, user sees a broken skeleton.
- *Intercept all JSON-RPC* — breaks the landing's own ORM calls
  (`get_no_role_landing_info`, `check_role_status`) and every Odoo subsystem
  that issues RPC on page load.
- *`ir.rule` per model* — no single model to attach to; this is a route-level
  concern, not a record-level one.
- *Exempt `base.group_erp_manager`* — too wide; many internal users may hold
  `erp_manager` through role implication without being administrators. The gate
  should only be bypassed by Settings-level administrators.
