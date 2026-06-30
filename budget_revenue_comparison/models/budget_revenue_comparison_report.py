# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

from odoo import _, api, models

from .formula import ActualResolver, BudgetResolver, eval_formula

_logger = logging.getLogger(__name__)

# KMITL accounting-dimension plan codes the report can filter on, in display
# order. Read from each line's ``analytic_distribution`` JSON. Only Department
# and Source apply here -- estimated revenue budget is not allocated by Fund or
# Activity, so those dimensions are intentionally excluded. ``sources`` is
# flat; ``departments`` is hierarchical (a pick also matches descendants).
DIMENSION_CODES = ("departments", "sources")
HIERARCHICAL_DIMS = ("departments",)

# The dimension that doubles as the optional group-by section axis (group by
# ส่วนงาน): excluded from the per-section filters and used as the section key.
GROUP_BY_DIM = "departments"

# A budget appropriation/transfer move; ``consume`` is excluded so the Budget
# column is the *Current Budget (a)* (initial + supplementary + transfers).
BUDGET_MOVE_TYPES = ("appropriation", "entry")

# GL income account types -- used only to bound the auto-discovery of which
# departments appear in the revenue data (the row formulas still decide what
# actually counts in each figure).
INCOME_TYPES = ("income", "income_other")


class BudgetRevenueComparisonReport(models.AbstractModel):
    """Budget-vs-Actual revenue report.

    One shared compute (:meth:`get_comparison_data`) feeds the OWL client
    action (over RPC) and the XLSX export, so screen and spreadsheet always
    agree. Each configured row's Budget figure comes from ``budget.move``
    (revenue codes, full fiscal year) and its Actual figure from
    ``account.move.line`` (income postings, to the as-of date) -- two
    independent formulas because the budget chart and the CoA have no link.
    """

    _name = "budget.revenue.comparison.report"
    _description = "Budget Revenue Comparison Report"

    # ------------------------------------------------------------------
    # Dimension filtering (inlined; this module does not depend on
    # accounting_kmitl_reports). Same ``analytic_distribution`` leaves the
    # other KMITL reports build, applied to both the budget and the GL side.
    # ------------------------------------------------------------------
    @api.model
    def _build_dim_leaves(self, dims):
        analytic = self.env["account.analytic.account"]
        use_child = "parent_id" in analytic._fields
        leaves = []
        for code in DIMENSION_CODES:
            ids = (dims or {}).get(code) or []
            if not ids:
                continue
            if code in HIERARCHICAL_DIMS and use_child:
                ids = analytic.search([("id", "child_of", ids)]).ids
            leaves.append(("analytic_distribution", "in", ids))
        return leaves

    @api.model
    def _state_leaf(self, only_posted):
        return (
            [("parent_state", "=", "posted")]
            if only_posted
            else [("parent_state", "!=", "cancel")]
        )

    # ------------------------------------------------------------------
    # Domain builders + per-side aggregation. ``leaves`` are extra domain
    # leaves (dimension filters and/or a per-department group scope), so the
    # same aggregators serve the flat report, each department section and the
    # grand total -- one read_group per call regardless of formula count.
    # ------------------------------------------------------------------
    @api.model
    def _budget_domain(self, options, leaves):
        return [
            ("company_id", "=", options["company_id"]),
            ("account_fiscal_year_id", "=", options["fiscal_year_id"]),
            ("budget_type", "=", "revenue"),
            ("move_type", "in", list(BUDGET_MOVE_TYPES)),
        ] + self._state_leaf(options["only_posted"]) + list(leaves)

    @api.model
    def _actual_domain(self, options, leaves):
        return [
            ("company_id", "=", options["company_id"]),
            ("date", ">=", options["date_from"]),
            ("date", "<=", options["date_to"]),
        ] + self._state_leaf(options["only_posted"]) + list(leaves)

    @api.model
    def _aggregate_budget(self, options, leaves):
        """``{budget_code: balance}`` of the current revenue budget for the
        whole fiscal year (appropriation + entry, excluding consume)."""
        if not options.get("fiscal_year_id"):
            return {}
        groups = self.env["budget.move.line"].read_group(
            self._budget_domain(options, leaves), ["balance:sum"], ["code"]
        )
        return {
            g["code"]: (g.get("balance") or 0.0) for g in groups if g.get("code")
        }

    @api.model
    def _aggregate_actual(self, options, leaves):
        """List of ``{'code', 'type', 'value'}`` for GL accounts with activity
        in the date range, where ``value`` is credit-positive (``credit -
        debit``) so revenue reads as a positive number. No account_type
        restriction on purpose: the row's actual formula scopes the accounts
        (``A['income']`` by type, ``A['41%']`` by code), so pre-aggregating
        every account keeps code-based selectors working for non-income
        accounts too."""
        if not options.get("date_from") or not options.get("date_to"):
            return []
        groups = self.env["account.move.line"].read_group(
            self._actual_domain(options, leaves),
            ["debit:sum", "credit:sum"],
            ["account_id"],
        )
        acc_ids = [g["account_id"][0] for g in groups if g.get("account_id")]
        info = {
            a.id: (a.code or "", a.account_type or "")
            for a in self.env["account.account"].browse(acc_ids)
        }
        accounts = []
        for g in groups:
            acc = g.get("account_id")
            if not acc:
                continue
            code, atype = info.get(acc[0], ("", ""))
            accounts.append(
                {
                    "code": code,
                    "type": atype,
                    "value": (g.get("credit") or 0.0) - (g.get("debit") or 0.0),
                }
            )
        return accounts

    # ------------------------------------------------------------------
    # Shared compute
    # ------------------------------------------------------------------
    @api.model
    def get_comparison_data(self, options):
        """Compute the report for ``options`` and return JSON-friendly rows.

        ``options`` keys: ``company_id``, ``fiscal_year_id`` (drives the
        full-year Budget column), ``date_from`` / ``date_to`` (drive the
        to-date Actual column), ``only_posted`` (bool), ``dims``
        (``{code: [analytic_account_ids]}``) and ``group_by_department``
        (bool). Each row is ``{id, row_type, name, budget, actual,
        percentage}``; ``header`` and ``department`` rows carry ``None`` for
        the three figures.
        """
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        # Normalise once so the aggregators read a complete options dict.
        options = dict(
            options,
            company_id=company_id,
            only_posted=bool(options.get("only_posted", True)),
        )
        dims = options.get("dims") or {}

        lines = self.env["budget.revenue.report.line"].search(
            [("company_id", "=", company_id)], order="sequence, id"
        )

        if options.get("group_by_department"):
            rows = self._grouped_rows(options, lines, dims)
        else:
            rows = self._section_rows(options, lines, self._build_dim_leaves(dims))

        return {"rows": rows, "currency_id": company.currency_id.id}

    @api.model
    def _section_rows(self, options, lines, leaves):
        """The indicator rows (report body) computed against ``leaves`` --
        reused for the flat report, each department section and the total."""
        budget = BudgetResolver(self._aggregate_budget(options, leaves))
        actual = ActualResolver(self._aggregate_actual(options, leaves))
        rows = []
        for line in lines:
            if line.row_type == "header":
                rows.append(self._row(line, None, None))
                continue
            budget_amount = self._eval(line, line.budget_formula, budget, actual)
            actual_amount = self._eval(line, line.actual_formula, budget, actual)
            rows.append(self._row(line, budget_amount, actual_amount))
        return rows

    # ------------------------------------------------------------------
    # Group by department -- the department dimension becomes a section axis;
    # the other three dimensions still filter within each section. The grouping
    # is derived from ``analytic_distribution`` only (no reliance on the stored
    # department_analytic_id mirror).
    # ------------------------------------------------------------------
    @api.model
    def _grouped_rows(self, options, lines, dims):
        dims_wo_dept = {k: v for k, v in dims.items() if k != GROUP_BY_DIM}
        base_leaves = self._build_dim_leaves(dims_wo_dept)
        rows = []
        for name, dept_leaf in self._department_groups(options, dims, base_leaves):
            section = self._section_rows(options, lines, base_leaves + [dept_leaf])
            if not self._section_has_data(section):
                continue
            rows.append(self._section_header_row(name))
            rows.extend(section)
        # Grand total: respects an explicit department selection, else all data.
        rows.append(self._section_header_row(_("รวมทุกส่วนงาน")))
        rows.extend(self._section_rows(options, lines, self._build_dim_leaves(dims)))
        return rows

    @api.model
    def _department_groups(self, options, dims, base_leaves):
        """Yield ``(name, leaf)`` per department section. Explicitly selected
        departments roll up their descendants (``child_of``); auto-discovered
        departments use their exact id so the sections stay disjoint."""
        Analytic = self.env["account.analytic.account"]
        selected = dims.get(GROUP_BY_DIM) or []
        if selected:
            for dept in Analytic.browse(selected).exists():
                ids = Analytic.search([("id", "child_of", dept.id)]).ids
                yield dept.display_name, ("analytic_distribution", "in", ids)
        else:
            for dept in Analytic.browse(self._discover_department_ids(options, base_leaves)):
                yield dept.display_name, ("analytic_distribution", "in", [dept.id])

    @api.model
    def _discover_department_ids(self, options, base_leaves):
        """Department analytic accounts that actually appear in the period's
        data, extracted from the ``analytic_distribution`` JSON of both the
        revenue budget lines and the income GL lines (ordered by the analytic
        plan for a stable display)."""
        dept_ids = set(
            self.env["account.analytic.account"]
            .search([("root_plan_id.code", "=", "departments")])
            .ids
        )
        if not dept_ids:
            return []
        sources = []
        if options.get("fiscal_year_id"):
            sources.append(
                ("budget.move.line", self._budget_domain(options, base_leaves))
            )
        if options.get("date_from") and options.get("date_to"):
            sources.append(
                (
                    "account.move.line",
                    self._actual_domain(options, base_leaves)
                    + [("account_id.account_type", "in", list(INCOME_TYPES))],
                )
            )
        present = set()
        for model, domain in sources:
            for rec in self.env[model].search_read(domain, ["analytic_distribution"]):
                for key in rec.get("analytic_distribution") or {}:
                    try:
                        aid = int(key)
                    except (TypeError, ValueError):
                        continue
                    if aid in dept_ids:
                        present.add(aid)
        return (
            self.env["account.analytic.account"]
            .search([("id", "in", list(present))])
            .ids
        )

    @api.model
    def _section_header_row(self, name):
        return {
            "id": 0,
            "row_type": "department",
            "name": name,
            "budget": None,
            "actual": None,
            "variance": None,
            "percentage": None,
        }

    @api.model
    def _section_has_data(self, section):
        """A section is worth showing if any indicator row carries a non-zero
        budget or actual figure."""
        return any(row["budget"] or row["actual"] for row in section)

    @api.model
    def _row(self, line, budget_amount, actual_amount):
        # Percentage is meaningful only against a non-zero budget; the OWL/XLSX
        # layers render ``None`` as a dash. Variance = Actual - Budget (positive
        # means revenue exceeded the target).
        percentage = (
            (actual_amount / budget_amount * 100.0) if budget_amount else None
        )
        variance = (
            actual_amount - budget_amount
            if actual_amount is not None and budget_amount is not None
            else None
        )
        return {
            "id": line.id,
            "row_type": line.row_type,
            "name": line.name,
            "budget": budget_amount,
            "actual": actual_amount,
            "variance": variance,
            "percentage": percentage,
        }

    @api.model
    def _eval(self, line, formula, budget, actual):
        """Evaluate one formula, never letting a bad row crash the whole
        report (formulas are validated on save, so this is belt-and-braces)."""
        try:
            return eval_formula(formula, budget, actual)
        except Exception:  # noqa: BLE001
            _logger.warning(
                "budget_revenue_comparison: bad formula on row %s (%s): %s",
                line.id,
                line.name,
                formula,
            )
            return 0.0

    # ------------------------------------------------------------------
    # XLSX export -- return the report action so the OWL client action can
    # ``doAction`` it. Filters travel in ``data`` (no persisted state), so the
    # spreadsheet mirrors the screen exactly.
    # ------------------------------------------------------------------
    @api.model
    def action_export_xlsx(self, options):
        options = options or {}
        carrier = self.env["budget.revenue.comparison.wizard"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "fiscal_year_id": options.get("fiscal_year_id"),
                "date_from": options.get("date_from"),
                "date_to": options.get("date_to"),
            }
        )
        report = self.env.ref(
            "budget_revenue_comparison.action_report_budget_revenue_comparison_xlsx"
        )
        return report.report_action(carrier, data={"options": options})


class BudgetRevenueComparisonXlsx(models.AbstractModel):
    """XLSX export -- shares the compute with the screen so the two agree."""

    _name = "report.budget_revenue_comparison.report_xlsx"
    _description = "Budget Revenue Comparison XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        report = self.env["budget.revenue.comparison.report"]
        result = report.get_comparison_data(options)
        rows = result["rows"]
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet(_("Budget vs Actual Revenue"))
        bold = workbook.add_format({"bold": True})
        num = workbook.add_format({"num_format": "#,##0.00"})
        num_bold = workbook.add_format({"bold": True, "num_format": "#,##0.00"})
        pct = workbook.add_format({"num_format": '#,##0.00"%"'})
        pct_bold = workbook.add_format({"bold": True, "num_format": '#,##0.00"%"'})
        center = workbook.add_format({"align": "center"})
        # Variance: green when revenue >= budget, red when short.
        var_pos = workbook.add_format({"num_format": "#,##0.00", "font_color": "#1c7c3a"})
        var_neg = workbook.add_format({"num_format": "#,##0.00", "font_color": "#c0392b"})
        var_pos_bold = workbook.add_format(
            {"bold": True, "num_format": "#,##0.00", "font_color": "#1c7c3a"}
        )
        var_neg_bold = workbook.add_format(
            {"bold": True, "num_format": "#,##0.00", "font_color": "#c0392b"}
        )

        label_fmt = {
            "department": workbook.add_format(
                {"bold": True, "bg_color": "#e9ecef", "top": 1}
            ),
            "header": workbook.add_format({"bold": True}),
            "line": workbook.add_format({"indent": 1}),
            "total": workbook.add_format({"bold": True, "top": 1, "indent": 1}),
        }

        sheet.merge_range(0, 0, 0, 4, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 4, _("Budget vs Actual Revenue"), bold)
        sheet.merge_range(
            2,
            0,
            2,
            4,
            "%s %s %s %s"
            % (
                _("From"),
                options.get("date_from") or "",
                _("to"),
                options.get("date_to") or "",
            ),
        )

        headers = [
            _("Indicator"),
            _("Budget"),
            _("Actual"),
            _("Variance"),
            _("%"),
        ]
        for col, title in enumerate(headers):
            sheet.write(4, col, title, bold if col == 0 else center)

        r = 5
        for row in rows:
            # Every row type except a plain "line" is emphasised (headers,
            # department sections and totals).
            bold_row = row["row_type"] != "line"
            sheet.write(r, 0, row["name"] or "", label_fmt.get(row["row_type"]))
            if row["budget"] is not None:
                sheet.write_number(r, 1, row["budget"], num_bold if bold_row else num)
            if row["actual"] is not None:
                sheet.write_number(r, 2, row["actual"], num_bold if bold_row else num)
            if row["variance"] is not None:
                if row["variance"] < 0:
                    var_fmt = var_neg_bold if bold_row else var_neg
                else:
                    var_fmt = var_pos_bold if bold_row else var_pos
                sheet.write_number(r, 3, row["variance"], var_fmt)
            if row["percentage"] is not None:
                sheet.write_number(
                    r, 4, row["percentage"], pct_bold if bold_row else pct
                )
            elif row["row_type"] in ("line", "total"):
                sheet.write(r, 4, "–", center)
            r += 1

        sheet.set_column(0, 0, 48)
        sheet.set_column(1, 3, 18)
        sheet.set_column(4, 4, 12)
