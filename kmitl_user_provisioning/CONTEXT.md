# KMITL User Provisioning

Gates internal users who exist but have not yet been set up for real work, so they meet a clear "contact admin" page instead of an empty, confusing home they might poke around in.

## Language

### Concepts

**Provisioned user**:
An internal user who is ready to work — either linked to an `hr.employee` (the normal path, done by HR) **or** deliberately granted a functional group by an admin (the override path). A provisioned user logs in to the normal home.
_Avoid_: activated, enabled

**Un-provisioned user**:
An internal user (`base.group_user`) who is **not** an admin, has **no** linked `hr.employee`, and carries **no** functional group beyond the default set every new account gets. This is the state a freshly created account sits in until someone sets it up. An un-provisioned user is shown the Provisioning Notice on login. Business apps are already invisible/inaccessible to them through Odoo's own access layer — this module only changes what they *land on*, it never removes groups.
_Avoid_: locked-out user (nothing is taken away), disabled user (they can still log in)

**Provisioning Notice**:
The full-screen "บัญชีของคุณยังไม่ได้รับสิทธิ์การใช้งาน — กรุณาติดต่อผู้ดูแลระบบ" landing page shown to an un-provisioned user on login, with the company's contact details and a log-out button. Reached only as the user's home action, never as an app/menu.

**Admin** (in this context):
A user excluded from the gate regardless of employee link: the superuser, or anyone in `base.group_system` (Settings). These are the people who do the provisioning, so they must never be gated.
