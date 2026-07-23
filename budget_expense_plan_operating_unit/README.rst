========================================
Budget Expense Plan with Operating Units
========================================

Adds Operating Unit scoping to the Expense Plan (``budget_expense_plan``).

A Plan Document carries an ``operating_unit_id`` (defaulting to the user's
operating unit). A global record rule limits visibility to documents whose
Operating Unit is among the user's allowed units — documents with no OU stay
visible to everyone (the central-planning escape hatch).
