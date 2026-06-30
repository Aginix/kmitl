# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import logging

from odoo import _, api, models

from .formula import ActualResolver, BudgetResolver, eval_formula

_logger = logging.getLogger(__name__)

# KMITL accounting-dimension plan codes the report can filter on, in display
# order. Read from each line's ``analytic_distribution`` JSON. ``sources`` is
# flat; the rest are hierarchical (a pick also matches descendants).
DIMENSION_CODES = ("departments", "sources", "funds", "activities")
HIERARCHICAL_DIMS = ("departments", "funds", "activities")

# A budget appropriation/transfer move; ``consume`` is excluded so the Budget
# column is the *Current Budget (a)* (initial + supplementary + transfers).
BUDGET_MOVE_TYPES = ("appropriation", "entry")


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
    # Per-side aggregation -- one read_group each, regardless of how many rows
    # or brackets the formulas use.
    # ------------------------------------------------------------------
    @api.model
    def _aggregate_budget(self, options):
        """``{budget_code: balance}`` of the current revenue budget for the
        whole fiscal year (appropriation + entry, excluding consume)."""
        fy_id = options.get("fiscal_year_id")
        if not fy_id:
            return {}
        domain = [
            ("company_id", "=", options["company_id"]),
            ("account_fiscal_year_id", "=", fy_id),
            ("budget_type", "=", "revenue"),
            ("move_type", "in", list(BUDGET_MOVE_TYPES)),
        ] + self._state_leaf(options["only_posted"]) + self._build_dim_leaves(
            options.get("dims") or {}
        )
        groups = self.env["budget.move.line"].read_group(
            domain, ["balance:sum"], ["code"]
        )
        return {
            g["code"]: (g.get("balance") or 0.0) for g in groups if g.get("code")
        }

    @api.model
    def _aggregate_actual(self, options):
        """List of ``{'code', 'type', 'value'}`` for GL accounts with activity
        in the date range, where ``value`` is credit-positive (``credit -
        debit``) so revenue reads as a positive number."""
        date_from = options.get("date_from")
        date_to = options.get("date_to")
        if not date_from or not date_to:
            return []
        # No account_type restriction here on purpose: the row's actual formula
        # is what scopes the accounts (``A['income']`` by type, ``A['41%']`` by
        # code), so pre-aggregating every account keeps code-based selectors
        # working for accounts that are not income-typed.
        domain = [
            ("company_id", "=", options["company_id"]),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ] + self._state_leaf(options["only_posted"]) + self._build_dim_leaves(
            options.get("dims") or {}
        )
        groups = self.env["account.move.line"].read_group(
            domain, ["debit:sum", "credit:sum"], ["account_id"]
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
        to-date Actual column), ``only_posted`` (bool) and ``dims``
        (``{code: [analytic_account_ids]}``). Each row is
        ``{id, row_type, name, budget, actual, percentage}`` -- header rows
        carry ``None`` for the three figures.
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

        lines = self.env["budget.revenue.report.line"].search(
            [("company_id", "=", company_id)], order="sequence, id"
        )

        budget = BudgetResolver(self._aggregate_budget(options))
        actual = ActualResolver(self._aggregate_actual(options))

        rows = []
        for line in lines:
            if line.row_type == "header":
                rows.append(self._row(line, None, None))
                continue
            budget_amount = self._eval(line, line.budget_formula, budget, actual)
            actual_amount = self._eval(line, line.actual_formula, budget, actual)
            rows.append(self._row(line, budget_amount, actual_amount))

        return {"rows": rows, "currency_id": company.currency_id.id}

    @api.model
    def _row(self, line, budget_amount, actual_amount):
        # Percentage is meaningful only against a non-zero budget; the OWL/XLSX
        # layers render ``None`` as a dash.
        percentage = (
            (actual_amount / budget_amount * 100.0) if budget_amount else None
        )
        return {
            "id": line.id,
            "row_type": line.row_type,
            "name": line.name,
            "budget": budget_amount,
            "actual": actual_amount,
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

        label_fmt = {
            "header": workbook.add_format({"bold": True}),
            "line": workbook.add_format({"indent": 1}),
            "total": workbook.add_format({"bold": True, "top": 1, "indent": 1}),
        }
        is_bold = {"header", "total"}

        sheet.merge_range(0, 0, 0, 3, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 3, _("Budget vs Actual Revenue"), bold)
        sheet.merge_range(
            2,
            0,
            2,
            3,
            "%s %s %s %s"
            % (
                _("From"),
                options.get("date_from") or "",
                _("to"),
                options.get("date_to") or "",
            ),
        )

        headers = [_("Indicator"), _("Budget"), _("Actual"), _("%")]
        for col, title in enumerate(headers):
            sheet.write(4, col, title, bold if col == 0 else center)

        r = 5
        for row in rows:
            bold_row = row["row_type"] in is_bold
            sheet.write(r, 0, row["name"] or "", label_fmt.get(row["row_type"]))
            if row["budget"] is not None:
                sheet.write_number(r, 1, row["budget"], num_bold if bold_row else num)
            if row["actual"] is not None:
                sheet.write_number(r, 2, row["actual"], num_bold if bold_row else num)
            if row["percentage"] is not None:
                sheet.write_number(
                    r, 3, row["percentage"], pct_bold if bold_row else pct
                )
            elif row["row_type"] != "header":
                sheet.write(r, 3, "–", center)
            r += 1

        sheet.set_column(0, 0, 48)
        sheet.set_column(1, 2, 18)
        sheet.set_column(3, 3, 12)
