# ADR-0016 — User-defined Route Templates and Per-record Visibility

**Status:** Accepted  
**Date:** 2026-08-25  
**Module:** `agx_sarabun_user_template` (new) + `agx_sarabun` (chatter/description)

---

## Context

`sarabun.route.template` was originally a **manager-only catalogue**: the
Configuration menu is gated to `group_sarabun_manager`, ACL grants users read-only
access, and the ir.rule `sarabun_route_template_read_rule` opens every template to
every user (`[(1,'=',1)]`). Regular sarabun users could not create routing shortcuts
for themselves.

The requirement is to let regular `group_sarabun_user` members define their own route
templates and control who sees them, while leaving manager-administered templates
unchanged. Two small core improvements (chatter and description field exposure) are
bundled with the main feature.

---

## Decision

### 1. Three-tier `visibility` Selection

A `visibility` field (Selection, required, default `'public'`) is added to
`sarabun.route.template`:

| Value | Thai label | Who sees it |
|---|---|---|
| `personal` | ส่วนตัว | Owner only (`owner_id = user`) |
| `unit` | ทั้งหน่วยงาน | Owner + members of `department_id` **and its sub-departments** |
| `public` | ทุกคน | All sarabun users |

`default='public'` is chosen deliberately so **existing manager/seed templates keep
their current all-user visibility after upgrade** without any data migration.

### 2. `public` is Manager-only

An `@api.constrains('visibility')` guard raises `ValidationError` if a
non-manager attempts to save `visibility='public'`. Enforced server-side to be robust
regardless of which form or API call triggers the save.

### 3. `owner_id` Field (not `create_uid`)

An explicit `owner_id = fields.Many2one('res.users')` field is added, defaulting to
`self.env.user` on creation. Using an explicit owner field (the same pattern as
`sarabun.document.sender_user_id` and `mail.activity.todo.log.user_id`) is preferred
over `create_uid` because:

- It can be seen and reasoned about in the UI and ir.rules without chasing ORM internals.
- A manager can later reassign ownership explicitly if needed.
- `copy=False` ensures duplicate templates don't inherit the original owner.

### 4. Unit Sharing via `hr.department.parent_path` (Hierarchy, not Flat Match)

The `department_id` field already on `sarabun.route.template` (used for auto-matching)
doubles as the "share-to unit" for `unit` visibility. A template shared at department X
is visible to members of **X and all of X's sub-departments**. This is implemented via
a non-stored computed field on `res.users`:

```python
sarabun_shared_department_ids = fields.Many2many(
    "hr.department", compute="_compute_sarabun_shared_department_ids", compute_sudo=True
)
```

The computation walks `employee_id.department_id.parent_path` (a `/`-delimited string
of ancestor IDs maintained by Odoo's `_parent_store`). `parent_path='1/5/12/'` →
`[1, 5, 12]` = the user's dept + all ancestors. The ir.rule then checks
`department_id in user.sarabun_shared_department_ids.ids`, which is satisfied when the
template's dept is the viewer's own dept **or any ancestor** — i.e., shared downward
through the sub-tree.

`compute_sudo=True` is required so the computation can read `hr.employee.department_id`
even for users who lack HR read access.

### 5. Read Rule Override (not Supplement)

The existing `agx_sarabun.sarabun_route_template_read_rule` (group: `group_sarabun_user`,
domain: `[(1,'=',1)]`) is **replaced** (same xmlid, new domain) rather than adding a
second rule. This is necessary because within a group, multiple ir.rules are OR-combined:
keeping the old `[(1,'=',1)]` alongside a new visibility rule would make the visibility
rule a no-op (since `(1=1) OR (anything) = True`).

New domain:
```python
['|','|',
    ('visibility','=','public'),
    ('owner_id','=',user.id),
    '&',('visibility','=','unit'),
        ('department_id','in',user.sarabun_shared_department_ids.ids)]
```

### 6. Manager Rules (Bypass of User-group Restrictions)

`group_sarabun_manager` implies `group_sarabun_user`. Odoo OR-combines ir.rules from
**all groups the user belongs to** (including via implied membership). Without explicit
manager rules, adding user-group visibility rules would unintentionally restrict managers
to their own templates.

The new module therefore adds full-access `[(1,'=',1)]` rules on both
`sarabun.route.template` and `sarabun.route.template.line` for `group_sarabun_manager`,
restoring unconditional manager access.

### 7. ACL Grants (User CRUD) Paired with Write ir.Rules

The existing ACL for `group_sarabun_user` on both template models is read-only (`1,0,0,0`).
The new module adds supplemental rows granting `1,1,1,1` — Odoo ACL entries are OR/max-
combined, so the effective ACL becomes full CRUD. The ir.rules then narrow write/create/
unlink to records where `owner_id = user.id` (templates) or `template_id.owner_id = user.id`
(lines).

### 8. `sarabun.route.template.line` Rules

Prior to this module, no ir.rule existed for `sarabun.route.template.line`. This left all
users reading all lines (fine for read-only access under the old flat model). The new
module adds:

- **User read rule**: same 3-branch visibility domain, traversed via `template_id.*`.
- **User write/create/unlink rule**: `template_id.owner_id = user.id`.
- **Manager full-access rule**: `[(1,'=',1)]`.

### 9. `origin_model_id` Stays Visible

Decision 3 in the Q&A: `origin_model_id` (and all other existing fields) remain visible
even for regular users ("เผื่อ user ที่รู้เรื่อง"). No field-level visibility gating is added.

### 10. Core Chatter + Description (Part A)

`agx_sarabun` core receives two small improvements bundled with the manifest version bump
(`16.0.5.1.0` → `16.0.5.2.0`):

- `SarabunRouteTemplate` inherits `mail.thread` and `mail.activity.mixin`; `name`,
  `active`, and `description` gain `tracking=True`.
- The form view surfaces the `description` field and appends a standard `oe_chatter`
  div for the message thread and activities.

---

## Alternatives Considered

**Flat department match (no hierarchy walk)**: Simpler, but would require template
owners to add a separate template for each sub-department, which defeats the purpose of
unit sharing.

**`create_uid` instead of `owner_id`**: `create_uid` is invisible in the UI and cannot
be reassigned. An explicit `owner_id` is more inspectable and follows established patterns
in this codebase.

**`res.config.settings` panel**: Rejected — a settings panel is for global configuration,
not per-user template management. A dedicated top-level menu + action is the correct UX.

**Supplementing the read rule**: Rejected — OR-combining with `[(1,'=',1)]` makes the
new domain a no-op. The wide original domain must be replaced.

**Two parallel menus (Configuration + "My Templates")**: Rejected — see revision below.

---

## Revision (2026-09-10): Single Unified Menu

The initial cut kept the original manager-only "Route Templates" entry under **Configuration**
alongside a new user-facing "แม่แบบเส้นทางของฉัน" at the root, so managers and users landed
in different places for what is now the same shared catalogue.

**Decision:** collapse to **one root-level menu — "แม่แบบเส้นทางอนุมัติ"** — reachable by
both roles. The old `agx_sarabun.menu_sarabun_route_template` under Configuration is
deactivated (`<field name="active" eval="False"/>`) rather than deleted, so its `action_*`
xmlid stays intact for any external reference.

Also removed: the `context={'default_visibility':'personal'}` override on the action.
`_default_visibility()` on the model already returns `personal` for regular users and
`public` for managers/superuser, so the context override was forcing managers into
`personal` unnecessarily. Deleting it lets the model default win for both roles.

---

## Consequences

- Existing manager/seed templates with no `owner_id` remain readable by all users via
  `visibility='public'` (the default). No data migration required.
- Both managers and regular users use the same root-level menu ("แม่แบบเส้นทางอนุมัติ");
  the read ir.rule scopes what each role sees, and `_default_visibility()` picks the right
  create-default per role.
- The `find_matching_templates` engine call is automatically scoped by the ir.rules —
  a user calling it at send time will only see templates they can read, which is the
  correct behaviour for user-created personal/unit templates.
- The deactivated Configuration entry (`menu_sarabun_route_template`) stays in the DB
  but is hidden from the sidebar; managers reach the same catalogue via the root menu.
