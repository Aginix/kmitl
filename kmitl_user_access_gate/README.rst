=====================
KMITL User Access Gate
=====================

When a user authenticates (e.g. via LDAP) but has no linked ``hr.employee``,
they have not yet been allocated permissions. This module revokes all of their
groups on login so they see no apps until an admin provisions them.

How it works
============

On login, ``res.users._update_last_login`` checks each user:

* the main admin (``base.user_admin``) and the superuser are always exempt;
* users with a linked ``hr.employee`` keep their access;
* portal/public users (share users) are left untouched;
* any remaining **internal** user without an employee has all groups cleared.

Once an admin links an employee and assigns groups, those groups are preserved
on subsequent logins.
