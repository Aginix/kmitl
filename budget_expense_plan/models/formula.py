# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Single-namespace formula engine for the expense-plan Actual column.

Each Budget Line carries one free-text ``expr`` evaluated with Odoo's
``safe_eval``. It references budget codes through ``A['<pat>']`` -> the period
sum of เบิกจ่ายจริง (consume) for every matching ``budget.account`` code::

    A['52400%']                      # all codes starting 52400
    A['5101010038'] + A['5101010040']

``A`` is a resolver object exposing ``__getitem__`` so ``A['52%']`` becomes
``A.__getitem__('52%')``. Full arithmetic (``+ - * / ()`` and numeric
constants) is allowed; nothing else, because ``safe_eval`` exposes only ``A``
(no builtins).

The selectors are SQL-``LIKE``-flavoured (``%`` = any run, ``_`` = one char).
Adapted from ``budget_revenue_comparison.models.formula``; here there is a
single namespace over budget codes (both the plan and its actual live in the
budget-code namespace, so no CoA disambiguation is needed).
"""
import re
from functools import lru_cache

from odoo.tools.safe_eval import safe_eval


@lru_cache(maxsize=512)
def _like_to_regex(pattern):
    """Compile an SQL-``LIKE``-style pattern (``%`` any run, ``_`` one char)
    into an anchored, case-insensitive regex. Cached: patterns come from a
    small fixed set of configured formulas reused across rows and months."""
    parts = []
    for ch in pattern or "":
        if ch == "%":
            parts.append(".*")
        elif ch == "_":
            parts.append(".")
        else:
            parts.append(re.escape(ch))
    return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


class CodeResolver:
    """``A['<code-pattern>']`` -> Σ consume of matching budget codes. Fed a
    ``{code: value}`` mapping pre-aggregated for one month + dimension slice."""

    __slots__ = ("_by_code",)

    def __init__(self, value_by_code):
        self._by_code = value_by_code or {}

    def __getitem__(self, pattern):
        if not (pattern or "").strip():
            raise ValueError("empty budget code selector A['']")
        rx = _like_to_regex(pattern)
        return sum(
            val for code, val in self._by_code.items() if code and rx.match(code)
        )


class _ZeroResolver:
    """Resolver used for validation: any bracket resolves to ``0.0`` so a
    formula can be dry-run to surface syntax / disallowed-name errors without
    touching the database."""

    def __getitem__(self, key):
        if not (key or "").strip():
            raise ValueError("empty budget code selector")
        return 0.0


def eval_formula(formula, resolver):
    """Evaluate one ``expr`` against the resolver, returning a float. Returns
    ``0.0`` for an empty formula. Raises whatever ``safe_eval`` raises (callers
    that must not crash should pre-validate or wrap)."""
    if not formula:
        return 0.0
    result = safe_eval(formula, {"A": resolver}, mode="eval")
    return float(result or 0.0)


def validate_formula(formula):
    """Compile + dry-run a formula with a zero-valued resolver. Returns
    ``None`` on success or a short error string on failure. Empty is valid."""
    if not formula:
        return None
    try:
        safe_eval(formula, {"A": _ZeroResolver()}, mode="eval")
    except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
        return str(exc) or exc.__class__.__name__
    return None
