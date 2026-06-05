# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.tools import date_utils, format_date

# Dimension plan codes this report can filter on. Order is the display order.
DIMENSION_CODES = ("departments", "sources", "funds", "activities")
# Hierarchical dimensions: a selected node also matches all of its descendants
# (when analytic accounts carry a ``parent_id`` hierarchy). ``sources`` is flat.
HIERARCHICAL_DIMS = ("departments", "funds", "activities")


class TrialBalanceReportKmitl(models.AbstractModel):
    """Trial balance computed by the OCA engine, extended with KMITL
    accounting-dimension filtering and a Debit/Credit/Balance layout.

    The same compute (:meth:`get_trial_balance_data`) feeds both the on-screen
    OWL client action (called over RPC) and the QWeb PDF, so the printout
    always mirrors the screen.
    """

    _name = "report.accounting_kmitl_reports.trial_balance_kmitl"
    _description = "KMITL Trial Balance Report"
    _inherit = "report.account_financial_report.trial_balance"

    # ------------------------------------------------------------------
    # Dimension filtering
    #
    # KMITL dimensions live in ``account.move.line.analytic_distribution``
    # (a JSON of {analytic_account_id: percentage}). We inject extra
    # ``analytic_distribution`` leaves into every move-line domain the OCA
    # engine builds, passing them through the context so we don't have to
    # touch the (re-used) OCA ``_get_data`` signature.
    # ------------------------------------------------------------------
    def _kmitl_dim_leaves(self):
        return self.env.context.get("kmitl_dim_leaves") or []

    def _get_initial_balances_bs_ml_domain(self, *args, **kwargs):
        domain = super()._get_initial_balances_bs_ml_domain(*args, **kwargs)
        return domain + self._kmitl_dim_leaves()

    def _get_initial_balances_pl_ml_domain(self, *args, **kwargs):
        domain = super()._get_initial_balances_pl_ml_domain(*args, **kwargs)
        return domain + self._kmitl_dim_leaves()

    @api.model
    def _get_period_ml_domain(self, *args, **kwargs):
        domain = super()._get_period_ml_domain(*args, **kwargs)
        return domain + self._kmitl_dim_leaves()

    def _get_initial_balance_fy_pl_ml_domain(self, *args, **kwargs):
        domain = super()._get_initial_balance_fy_pl_ml_domain(*args, **kwargs)
        return domain + self._kmitl_dim_leaves()

    @api.model
    def _kmitl_build_dim_leaves(self, dims):
        """Turn the selected dimension values into ``analytic_distribution``
        domain leaves. Within a dimension the ids (plus descendants for
        hierarchical dimensions) are OR-ed; the resulting leaves are AND-ed
        across dimensions by the domain builder.
        """
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

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_fy_start_date(self, date_from, company):
        """Fiscal-year start that contains ``date_from`` (used by the OCA
        engine to accumulate P&L opening balances)."""
        if not date_from:
            return False
        if isinstance(date_from, str):
            date_from = fields.Date.to_date(date_from)
        start, _end = date_utils.get_fiscal_year(
            date_from,
            day=company.fiscalyear_last_day,
            month=int(company.fiscalyear_last_month),
        )
        return start

    @api.model
    def _kmitl_apply_account_range(self, options, company_id, account_ids):
        """Expand an optional account code range into ``account_ids`` and
        merge it with any explicitly picked accounts."""
        code_from = options.get("account_code_from_id")
        code_to = options.get("account_code_to_id")
        if code_from and code_to:
            a_from = self.env["account.account"].browse(code_from)
            a_to = self.env["account.account"].browse(code_to)
            if a_from.code and a_to.code:
                ranged = self.env["account.account"].search(
                    [
                        ("company_id", "=", company_id),
                        ("code", ">=", a_from.code),
                        ("code", "<=", a_to.code),
                    ]
                )
                account_ids = list(set(account_ids) | set(ranged.ids))
        return account_ids

    # ------------------------------------------------------------------
    # Shared compute
    # ------------------------------------------------------------------
    @api.model
    def get_trial_balance_data(self, options):
        """Compute the trial balance for ``options`` and return JSON-friendly
        rows. Called over RPC by the OWL client action and internally by the
        QWeb report.

        ``options`` keys: ``company_id``, ``date_from``, ``date_to``,
        ``only_posted`` (bool), ``hide_account_at_0`` (bool), ``journal_ids``,
        ``partner_ids``, ``account_ids``, ``account_code_from_id``,
        ``account_code_to_id`` and ``dims`` (``{code: [analytic_account_ids]}``).
        """
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        date_from = options.get("date_from")
        date_to = options.get("date_to")

        empty = {
            "rows": [],
            "totals": self._kmitl_empty_totals(),
            "currency_id": company.currency_id.id,
        }
        if not date_from or not date_to:
            return empty

        only_posted = bool(options.get("only_posted", True))
        hide_account_at_0 = bool(options.get("hide_account_at_0", True))
        journal_ids = options.get("journal_ids") or []
        partner_ids = options.get("partner_ids") or []
        account_ids = list(options.get("account_ids") or [])
        account_ids = self._kmitl_apply_account_range(options, company_id, account_ids)

        fy_start_date = self._kmitl_fy_start_date(date_from, company)
        leaves = self._kmitl_build_dim_leaves(options.get("dims") or {})

        report = self.with_context(kmitl_dim_leaves=leaves)
        total_amount, accounts_data, _partners = report._get_data(
            account_ids,
            journal_ids,
            partner_ids,
            company_id,
            date_to,
            date_from,
            False,  # foreign_currency
            only_posted,
            False,  # show_partner_details
            hide_account_at_0,
            # No unaffected-earnings account: KMITL does not want the
            # "Undistributed Profits/Losses" row (which the OCA engine would
            # otherwise always append, even at zero).
            False,
            fy_start_date,
            False,  # grouped_by
        )

        rows = []
        totals = self._kmitl_empty_totals()
        for account_id in sorted(
            accounts_data, key=lambda a: accounts_data[a]["code"] or ""
        ):
            ta = total_amount.get(account_id, {})
            opening = ta.get("initial_balance") or 0.0
            debit = ta.get("debit") or 0.0
            credit = ta.get("credit") or 0.0
            ending = ta.get("ending_balance") or 0.0
            row = {
                "id": account_id,
                "code": accounts_data[account_id]["code"] or "",
                "name": accounts_data[account_id]["name"] or "",
                "opening_debit": opening if opening > 0 else 0.0,
                "opening_credit": -opening if opening < 0 else 0.0,
                "opening_balance": opening,
                "period_debit": debit,
                "period_credit": credit,
                "period_balance": debit - credit,
                "ending_debit": ending if ending > 0 else 0.0,
                "ending_credit": -ending if ending < 0 else 0.0,
                "ending_balance": ending,
            }
            rows.append(row)
            for key in totals:
                totals[key] += row[key]
        return {
            "rows": rows,
            "totals": totals,
            "currency_id": company.currency_id.id,
        }

    @api.model
    def _kmitl_empty_totals(self):
        return {
            "opening_debit": 0.0,
            "opening_credit": 0.0,
            "opening_balance": 0.0,
            "period_debit": 0.0,
            "period_credit": 0.0,
            "period_balance": 0.0,
            "ending_debit": 0.0,
            "ending_credit": 0.0,
            "ending_balance": 0.0,
        }

    @api.model
    def _kmitl_format_amount(self, value):
        """Shared number formatting (kept identical to the OWL side so the PDF
        mirrors the screen). Blank for ~zero to reduce clutter."""
        if not value or abs(value) < 0.005:
            return ""
        return "{:,.2f}".format(value)

    # ------------------------------------------------------------------
    # PDF export — return the report action so the OWL client action can
    # ``doAction`` it. Filters travel in ``data`` so the PDF mirrors the
    # on-screen report exactly (no persisted record needed).
    # ------------------------------------------------------------------
    @api.model
    def action_print_pdf(self, options):
        options = options or {}
        # A throwaway carrier record anchors the report action (reusing the
        # standard ``report_action`` plumbing). The figures themselves travel
        # in ``data`` so the PDF mirrors the screen.
        carrier = self.env["trial.balance.report.wizard.kmitl"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "date_from": options.get("date_from"),
                "date_to": options.get("date_to"),
            }
        )
        report = self.env.ref(
            "accounting_kmitl_reports.action_report_trial_balance_kmitl"
        )
        return report.report_action(carrier, data={"options": options})

    # ------------------------------------------------------------------
    # QWeb PDF rendering — reuse the shared compute, do NOT call the OCA
    # ``_get_report_values`` (it expects a column-based wizard we no longer
    # have a form for).
    # ------------------------------------------------------------------
    def _get_report_values(self, docids, data):
        data = data or {}
        options = data.get("options") or {}
        result = self.get_trial_balance_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": "trial.balance.report.wizard.kmitl",
            "docs": self.env["trial.balance.report.wizard.kmitl"].browse(docids or []),
            "res_company": company,
            "rows": result["rows"],
            "totals": result["totals"],
            "format_amount": self._kmitl_format_amount,
            "date_from_label": format_date(self.env, options.get("date_from")),
            "date_to_label": format_date(self.env, options.get("date_to")),
        }
