=============================
HR LDAP User Provisioning (KMITL)
=============================

Auto-links a ``res.users`` account to the ``hr.employee`` record that already
exists in the directory, matching on **work email**.

Context
=======

Production already holds employee records for the whole organisation, but user
logins were created manually for HR staff only. Rolling out logins to every
employee by hand does not scale.

Odoo's core ``auth_ldap`` already solves the *creation* side: with
``create_user`` enabled it auto-creates a ``res.users`` on the user's first
LDAP login (copied from the configured *Template User*). What it does **not**
do is connect that new user back to the existing employee record. This module
fills that gap.

How it works
============

* An ``on_create`` automated action on ``res.users`` calls
  ``_kmitl_link_employee_by_email()``, which finds the employee whose
  ``work_email`` equals the user's ``login`` (the full email) and sets
  ``employee.user_id``.
* The method is **best-effort and never raises** — it runs inside the LDAP
  login transaction, so a failure must not block the user's first login. Any
  problem is logged and can be recovered with the backfill action below.
* Matching is case-insensitive with an exact re-check, so ``_``/``%`` in an
  address cannot cause a wrong match.

Because the trigger is plain ``res.users`` creation, it also covers users
created manually in the UI and, in the future, users provisioned via
``auth_oidc`` / Keycloak — no change needed.

Setup
=====

#. Configure LDAP (*Settings > General Settings > LDAP*):

   * Tick **Create user**.
   * Set a **Template User** with exactly the baseline groups an ordinary
     employee should have — every auto-created user is a copy of it.
   * Use an LDAP filter that matches on the mail attribute so the stored
     ``login`` equals the email, e.g. ``(&(objectClass=person)(mail=%s))``.
   * Enable TLS / ``auth_ldaps`` so credentials are not sent in clear text.

#. Install this module.

#. Run the **one-time backfill** for users that already exist
   (*Settings > Technical > Automation > Server Actions >
   "KMITL: backfill link users to employees" > Run*).

Requirements
============

* ``work_email`` must be **unique and present** on employees — it is the join
  key. A constraint blocks new duplicates going forward (existing duplicates
  are not retroactively blocked, so install stays safe); audit legacy data
  before rollout.

Roadmap
=======

Designed to be auth-agnostic. When SSO moves to Keycloak (``auth_oidc``), keep
the user ``login`` as the email and the same automation keeps working.
