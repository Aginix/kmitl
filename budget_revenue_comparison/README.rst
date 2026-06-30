==================================
KMITL Budget Revenue Comparison
==================================

Configurable report that sets **budgeted revenue** (งบประมาณรายรับ) beside
**actual revenue** (รายรับจริง), row by row, for a fiscal period.

Because KMITL's budget chart (``budget.account``) and the accounting Chart of
Accounts (``account.account``) are parallel charts with **no stored link**,
each report row carries two independent free-text formulas — one over budget
codes, one over GL accounts.

Columns
=======

* **ตัวชี้วัด (Indicator)** — the row label
* **งบประมาณรายรับ (Budget)** — the *current* revenue budget for the whole
  fiscal year (posted ``budget.move`` lines on revenue codes, appropriation +
  entry, excluding consume)
* **รายรับจริง (Actual)** — recognized revenue from the General Ledger
  (posted ``account.move.line`` on income-type accounts) up to the chosen
  as-of date
* **%** — Actual ÷ Budget × 100 (dash when Budget is zero)

The full-year Budget vs to-date Actual asymmetry makes the percentage read as
"% of the annual revenue target realized so far".

Configuring rows
================

Configuration ▸ *ตัวชี้วัดเปรียบเทียบรายรับ* (Budget Manager only). Each row has:

* **ประเภทแถว (Row type)** — ``หัวข้อ`` (header, no figures) / ``รายการ`` (line) /
  ``รวม`` (total; emphasised, computed from its own formula)
* **ลำดับ (Sequence)** — drag to order
* **สูตรงบประมาณรายรับ (Budget formula)** — ``B['<code-pattern>']``, e.g.
  ``B['41%']`` (all revenue codes starting 41). Arithmetic ``+ - * / ()`` allowed.
* **สูตรรายรับจริง (Actual formula)** — ``A['<selector>']``, where an
  alphabetic selector matches ``account_type`` (``A['income']``) and a numeric
  selector matches the CoA code (``A['41%']``). Revenue is credit-positive, so
  no leading ``-`` is needed.

Formulas are validated on save and evaluated with Odoo ``safe_eval`` (no
builtins exposed).

Output
======

* Interactive OWL screen (budget *รายงาน* menu), filterable by fiscal year, an
  as-of date, posted-only, and the four KMITL accounting dimensions
  (department / source / fund / activity)
* XLSX export sharing the same compute

This module deliberately does **not** use OCA MIS Builder; see
``docs/adr/0001-bespoke-report-not-mis-builder.md`` and
``docs/adr/0002-two-namespace-formula-language.md``.
