# Each row carries two free-text formulas with `B[...]` / `A[...]` accessors

A report row's Budget figure and Actual figure come from two separate free-text formula fields evaluated by `safe_eval`: `budget_formula` references revenue budget codes via `B['<code-pattern>']`, and `actual_formula` references GL income accounts via `A['<account_type-or-code-pattern>']`. Each accessor resolves to the period sum for the matching accounts; full arithmetic (`+ - * / ()` and constants) is allowed. We chose typed formulas over the simpler "pick a set of accounts" because revenue rows genuinely need within-row arithmetic (e.g. gross income minus a refund sub-account).

Two deliberate semantics:
- **Disambiguation is automatic** on the actual side — an alphabetic selector (`A['income']`) means `account_type`, a numeric/`%` selector (`A['41%']`) means a CoA code pattern. No collision is possible because CoA codes are digits.
- **`A[...]` returns credit-positive** (`credit − debit`), so revenue reads as a positive number and a debit refund naturally reduces the figure — authors write natural positive formulas instead of the MIS-style leading `-`. `B[...]` returns `balance` as-is (a revenue appropriation is already a positive balance).

## Considered options

- **Many2many account selection (no expression)** — simplest and eval-free, but cannot express "revenue A minus refund B" inside one row, and newly-created accounts must be added by hand.
- **Code-pattern / `account_type` selector only (declarative domain, no arithmetic)** — auto-includes matching accounts and fits the numeric charts, but still no within-row arithmetic.
- **Free-text arithmetic expression (chosen)** — the only option that supports within-row `+`/`−`; the price is a `safe_eval` surface that must be locked down and validated.

## Consequences

- Formulas are compiled/validated on save (`@api.constrains`): only `B`/`A` resolvers and arithmetic are exposed to `safe_eval` (no builtins), and bad syntax or disallowed names raise `ValidationError`.
- For performance each side is pre-aggregated by account once per period, then each bracket resolves against that cache (the MIS-AEP "one query" approach) — formulas never trigger per-row queries.
- Cross-row subtotals are **not** auto-summed: a `total` row computes via its own formula (e.g. `B['4%']`), keeping the row list flat and sequence-ordered.
