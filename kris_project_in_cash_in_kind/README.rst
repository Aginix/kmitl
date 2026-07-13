====================================
KRIS Project — In Cash / In Kind
====================================

Add-on for ``kris_project`` that splits the contracted value of research projects
(category *งานวิจัย*, seed record ``kris_project.project_category_research``) into two
components:

* **In Cash** (ทุนเงินสด) — the cash portion KRIS actually receives from the client.
* **In Kind** (ทุนสิ่งของ) — matching funds (equipment, labour, materials) contributed
  by an external party that never flow through KRIS's cash accounts.

On research projects the base ``project_value`` becomes a stored derivation of
``in_cash + in_kind`` and every cash-flow computation (operating expense, maintenance
deduction, revenue remaining, installment total-mismatch warning) is repointed to a new
``cash_target`` field that equals ``in_cash``. Non-research projects are untouched — the
new fields are hidden and the compute is a no-op.

Installation
============

``kris_project_in_cash_in_kind`` depends on ``kris_project``. On install, a
``post_init_hook`` backfills ``in_cash = project_value`` for every existing research
project so the derivation lands on the same total.

Uninstall drops the new fields and restores the base ``kris_project`` behaviour cleanly.
