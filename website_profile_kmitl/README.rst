=========================
Website Profile (KMITL)
=========================

Treats internal users as already email-verified on the website profile.

Context
=======

``website_profile`` (used by eLearning and Forum) shows the banner
*"Your Account has not yet been verified."* to every logged-in user whose
``karma`` is ``0``. The only way out is the email-verification link, which
grants ``karma = 3``.

Users auto-created on their first LDAP login (``auth_ldap``), or created
manually by an administrator, never go through that flow, so staff who are
already authenticated by the institute keep seeing the banner.

How it works
============

* On ``res.users`` creation, every internal user (``share = False``) with
  ``karma = 0`` receives the same karma an email verification would grant
  (``VALIDATION_KARMA_GAIN = 3``). The write goes through the ORM, so a
  ``gamification.karma.tracking`` entry is recorded and the rank is recomputed.
* Portal/public users are untouched and still verify their email as usual.
* Karma 3 matches the default eLearning thresholds for commenting and voting
  on slides; reviewing a course still requires 10.

Existing users
==============

Only users created after installation are covered. For the existing
population, run once as a Python-code server action on ``res.users``::

    users = env["res.users"].sudo().search([("share", "=", False), ("karma", "=", 0)])
    users.write({"karma": 3})
    log("website_profile_kmitl: set karma=3 on %s users" % len(users))
