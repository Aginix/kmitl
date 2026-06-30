# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
"""Two-namespace formula engine for the budget-vs-actual-revenue report.

Each report row carries two free-text formulas evaluated with Odoo's
``safe_eval``:

* ``budget_formula`` references **revenue budget codes** through ``B['<pat>']``
* ``actual_formula`` references **GL income accounts** through ``A['<sel>']``

``B`` / ``A`` are resolver objects exposing ``__getitem__`` so a bracket like
``B['41%']`` becomes ``B.__getitem__('41%')`` -> the period sum for every
matching account. Full arithmetic (``+ - * / ()`` and numeric constants) is
allowed; nothing else is, because ``safe_eval`` exposes only ``B`` and ``A``
(no builtins).

The selectors are SQL-``LIKE``-flavoured (``%`` = any run, ``_`` = one char).
On the actual side an *alphabetic* selector (``A['income']``) matches
``account_type`` while a *numeric* selector (``A['41%']``) matches the CoA
``code`` -- unambiguous because CoA codes are digits.
"""
import re

from odoo.tools.safe_eval import safe_eval

# safe_eval globals are rebuilt fresh for every evaluation, so passing
# ``nocopy=True`` only avoids a redundant shallow copy of the 2-key mapping.
_EVAL_KW = {"mode": "eval", "nocopy": True}


def _like_to_regex(pattern):
    """Compile an SQL-``LIKE``-style pattern (``%`` any run, ``_`` one char)
    into an anchored, case-insensitive regex. Every other character is matched
    literally."""
    parts = []
    for ch in pattern or "":
        if ch == "%":
            parts.append(".*")
        elif ch == "_":
            parts.append(".")
        else:
            parts.append(re.escape(ch))
    return re.compile("^" + "".join(parts) + "$", re.IGNORECASE)


class BudgetResolver:
    """``B['<code-pattern>']`` -> Σ budgeted-revenue balance of matching budget
    codes. Fed a ``{code: balance}`` mapping pre-aggregated for the period."""

    __slots__ = ("_by_code",)

    def __init__(self, balance_by_code):
        self._by_code = balance_by_code

    def __getitem__(self, pattern):
        if not (pattern or "").strip():
            raise ValueError("empty budget code selector B['']")
        rx = _like_to_regex(pattern)
        return sum(
            bal for code, bal in self._by_code.items() if code and rx.match(code)
        )


class ActualResolver:
    """``A['<selector>']`` -> Σ credit-positive actual revenue of matching GL
    accounts. ``selector`` is read as a CoA ``code`` pattern when it is numeric
    (``A['41%']``), otherwise as an ``account_type`` pattern (``A['income']``,
    ``A['income%']``). Fed a list of ``{'code', 'type', 'value'}`` dicts where
    ``value`` is already ``credit - debit`` (so revenue is positive)."""

    __slots__ = ("_accounts",)

    def __init__(self, accounts):
        self._accounts = accounts

    def __getitem__(self, selector):
        sel = (selector or "").strip()
        if not sel:
            raise ValueError("empty account selector A['']")
        rx = _like_to_regex(sel)
        if sel.replace("%", "").replace("_", "").isdigit():
            # Numeric selector -> match the CoA account code.
            return sum(
                a["value"] for a in self._accounts if a["code"] and rx.match(a["code"])
            )
        # Alphabetic selector -> match the account_type.
        return sum(
            a["value"] for a in self._accounts if a["type"] and rx.match(a["type"])
        )


class _ZeroResolver:
    """Resolver used for validation: any bracket resolves to ``0.0`` so a
    formula can be compiled/evaluated to surface syntax or disallowed-name
    errors without touching the database."""

    def __getitem__(self, key):
        if not (key or "").strip():
            raise ValueError("empty account selector")
        return 0.0


def eval_formula(formula, budget_resolver, actual_resolver):
    """Evaluate one formula against the two resolvers, returning a float.
    Returns ``0.0`` for an empty formula. Raises whatever ``safe_eval`` raises
    (callers that must not crash should pre-validate or wrap)."""
    if not formula:
        return 0.0
    result = safe_eval(
        formula, {"B": budget_resolver, "A": actual_resolver}, **_EVAL_KW
    )
    return float(result or 0.0)


def validate_formula(formula):
    """Compile + dry-run a formula with zero-valued resolvers. Returns ``None``
    on success or a short error string on failure (syntax error, unknown name,
    disallowed construct). Empty formula is valid."""
    if not formula:
        return None
    try:
        zero = _ZeroResolver()
        safe_eval(formula, {"B": zero, "A": zero}, **_EVAL_KW)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
        return str(exc) or exc.__class__.__name__
    return None
