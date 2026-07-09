Known consumers
---------------

* ``procurement_assignment_kmitl`` — ``purchase.request`` and
  ``purchase.order``. Thin consumer: hook overrides only, no extra
  business rules on assignment.
* ``disbursement`` — ``disbursement.request``. Adds a routing-rule engine
  (``disbursement.assignment.rule``) on top of the mixin, plus a
  return-for-correction workflow specific to verification.

Companion module
----------------

* ``base_assignment_todo`` — data-only bridge. Tags the assignment
  activity type with a ``todo_category`` so notifications surface in the
  unified Todo inbox (``mail_activity_todo``).

Deferred / open work
--------------------

* **State gating.** A ``_assignment_allowed_states`` class attribute
  (mirroring ``base_tier_validation._state_from`` / ``_state_to``) is a
  natural next step so a consumer can declare "claiming is only valid in
  ``signed``". Today a consumer that needs this overrides
  ``action_assignment_assign_me`` and the wizard ``action_assign``.
* **Base tests.** The mixin has no direct unit tests; behaviour is covered
  by the two consumer test suites (``procurement_assignment_kmitl``,
  ``disbursement``). A dummy TransientModel test would let default hooks
  regress independently of the consumers.
* **Wizard field injection API.** Consumers can already
  ``_inherit = "assign.officer.wizard"`` to add fields (e.g. a mandatory
  comment). No dedicated API is provided.
