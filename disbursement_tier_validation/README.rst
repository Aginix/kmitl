===========================
Disbursement Tier Validation
===========================

Adds a two-tier sequential approval to the disbursement request
(``disbursement.request``) approval step, using OCA ``base_tier_validation``.

What it does
============

* Gates only the ``verified -> approved`` transition. The ``sign`` and
  ``verify`` steps (and the ``disbursement_sarabun`` coupling) are unchanged.
* Requires two approvals **in sequence**:

  #. หัวหน้างานบัญชี (Accounting Head)
  #. ผู้อำนวยการกองคลัง (Finance Director)

* The reviews are opened automatically when the officer validates
  (``action_validate``). The second tier cannot approve before the first
  (``approve_sequence``).
* Approving the final tier obligates and consumes the budget exactly once via
  the existing ``_action_approve_budget`` — nothing is consumed earlier.
* Rejecting at any tier drops the reviews and returns the request to
  ``draft`` for revision.
* Validating/rejecting opens the ``base_tier_validation`` comment dialog; its
  Thai translation is provided through ``i18n_th_tier_validation`` and this
  module.

Configuration
=============

Assign users the **Disbursement Accounting Head** and **Disbursement Finance
Director** roles (Settings > Users > Roles). Holders of each role become the
reviewers for the matching tier.

The two tiers are defined as ``tier.definition`` records in
``data/tier_definition.xml`` and can be adjusted per company.
