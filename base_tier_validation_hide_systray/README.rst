================================
Tier Validation Todo Bridge
================================

Auto-installed bridge between ``base_tier_validation`` (OCA) and
``mail_activity_todo``. It removes the OCA "Reviewer Menu" systray so the
unified Todo bell is the single inbox for every pending action across every
module.

This is intentionally a **hide-only** first cut. Routing every
``tier.review`` to a ``mail.activity`` on the target record — so that
non-WA tier-validated flows also surface in the unified inbox — is a
follow-up planned for this same module.
