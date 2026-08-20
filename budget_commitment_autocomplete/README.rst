============================
Budget Commitment Rich Picker
============================

A reservation (ใบจองงบประมาณ) is picked by *what it is for*, but the stock
Many2one dropdown shows only one line of plain text per option while
searching, discarding everything past the first line of ``name_get``.

This module upgrades the ``budget_commitment_info`` widget (from the
``budget`` module) in place — it does **not** register a separate widget
name and ships no views of its own. Every field already using
``widget="budget_commitment_info"`` (readonly display or editable
draw-down picker, in any current or future module) automatically renders a
multi-line dropdown option for each ``budget.commitment`` candidate — number,
title, state, the six financial dimensions and the amounts — the moment this
module is installed. Uninstalling it silently degrades every one of those
fields back to the plain single-line dropdown; no other module needs to
depend on this one or change any view.

The dropdown enrichment reuses the same ``get_reservation_info()`` payload
the info card already calls, batched once per set of options shown.

The info card itself is a form-only affordance: in a list/tree view it is
suppressed (``env.config.viewType == "list"``) so it doesn't render a full
card in every row.
