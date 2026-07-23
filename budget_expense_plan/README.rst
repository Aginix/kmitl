===========================
KMITL Budget Expense Plan
===========================

แผนการเบิกจ่ายประจำปีงบประมาณ (annual monthly expense/disbursement plan).

Each ส่วนงาน (department) plans how much it expects to เบิกจ่าย each month of a
fiscal year, per budget line, and that plan is set beside the actual
disbursement pulled from the budget ledger.

Concepts
========

* **รายการงบ (Budget Line, ``budget.expense.line``)** — a plannable column: a
  label + its Category (one of the five expense roots of ``budget.account``) +
  an ``expr`` (``A['<code>']`` over budget codes) that pulls the actual consume.
* **แม่แบบ (Template, ``budget.expense.template``)** — the central, shared grid,
  one per (แหล่งเงิน × ปีงบประมาณ): the Activities in scope and, under each, the
  (Fund, Budget Line) pairs that must be planned.
* **เอกสารแผน (Plan Document, ``budget.expense.plan``)** — a ส่วนงาน's instance
  of a Template holding the 12-month แผน figures. State: draft → confirmed
  (unit) → active (central approves and locks).
* **Actual (ผล)** — derived from ``budget.move.line`` consume, never entered.

See ``CONTEXT.md`` and ``docs/adr/`` for the design decisions.
