# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, models
from odoo.tools import format_date


class TrialBalanceReportKmitl(models.AbstractModel):
    """Trial balance computed by the OCA engine, extended with KMITL
    accounting-dimension filtering and a Debit/Credit/Balance layout.

    The same compute (:meth:`get_trial_balance_data`) feeds both the on-screen
    OWL client action (called over RPC) and the QWeb PDF, so the printout
    always mirrors the screen.
    """

    _name = "report.accounting_kmitl_reports.trial_balance_kmitl"
    _description = "KMITL Trial Balance Report"
    _inherit = [
        "report.account_financial_report.trial_balance",
        "accounting_kmitl_reports.dimension.filter.mixin",
    ]

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

    # ------------------------------------------------------------------
    # Shared compute
    #
    # ``_kmitl_fy_start_date`` and ``_kmitl_apply_account_range`` live on the
    # dimension filter mixin (shared with the General Ledger report).
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
    def _kmitl_report_action(self, options, report_xmlid):
        """Anchor a report action on a throwaway carrier record (reusing the
        standard ``report_action`` plumbing). The figures travel in ``data``
        so the output mirrors the screen."""
        options = options or {}
        carrier = self.env["trial.balance.report.wizard.kmitl"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "date_from": options.get("date_from"),
                "date_to": options.get("date_to"),
            }
        )
        report = self.env.ref(report_xmlid)
        return report.report_action(carrier, data={"options": options})

    @api.model
    def action_print_pdf(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_trial_balance_kmitl"
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_trial_balance_kmitl_xlsx"
        )

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


class TrialBalanceXlsxKmitl(models.AbstractModel):
    """XLSX export of the trial balance — shares the compute with the screen
    and the PDF, so all three stay in sync."""

    _name = "report.accounting_kmitl_reports.trial_balance_xlsx"
    _description = "KMITL Trial Balance XLSX"
    _inherit = "report.report_xlsx.abstract"

    # The three balance sections, each with Debit / Credit / Balance keys.
    _COLUMNS = (
        ("opening_debit", "opening_credit", "opening_balance"),
        ("period_debit", "period_credit", "period_balance"),
        ("ending_debit", "ending_credit", "ending_balance"),
    )

    def generate_xlsx_report(self, workbook, data, objs):
        data = data or {}
        options = data.get("options") or {}
        report = self.env["report.accounting_kmitl_reports.trial_balance_kmitl"]
        result = report.get_trial_balance_data(options)
        rows = result["rows"]
        totals = result["totals"]
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet(_("Trial Balance"))
        bold = workbook.add_format({"bold": True})
        head = workbook.add_format(
            {
                "bold": True,
                "bg_color": "#F0F0F0",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )
        cell = workbook.add_format({"border": 1})
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        num_bold = workbook.add_format(
            {"border": 1, "bold": True, "num_format": "#,##0.00"}
        )

        sheet.merge_range(0, 0, 0, 9, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 9, _("Trial Balance"), bold)
        sheet.merge_range(
            2,
            0,
            2,
            9,
            "%s %s %s %s"
            % (
                _("From"),
                options.get("date_from") or "",
                _("to"),
                options.get("date_to") or "",
            ),
        )

        row_top = 4
        sheet.merge_range(row_top, 0, row_top + 1, 0, _("Account"), head)
        sheet.merge_range(row_top, 1, row_top, 3, _("Opening"), head)
        sheet.merge_range(row_top, 4, row_top, 6, _("During Period"), head)
        sheet.merge_range(row_top, 7, row_top, 9, _("Ending"), head)
        for i, label in enumerate(
            [_("Debit"), _("Credit"), _("Balance")] * 3, start=1
        ):
            sheet.write(row_top + 1, i, label, head)

        def write_amounts(row_idx, values, fmt):
            for col, value in enumerate(values, start=1):
                if not value or abs(value) < 0.005:
                    sheet.write_blank(row_idx, col, None, fmt)
                else:
                    sheet.write_number(row_idx, col, value, fmt)

        r = row_top + 2
        for row in rows:
            sheet.write(r, 0, "%s - %s" % (row["code"], row["name"]), cell)
            write_amounts(
                r, [row[k] for group in self._COLUMNS for k in group], num
            )
            r += 1

        sheet.write(r, 0, _("Total"), num_bold)
        write_amounts(
            r, [totals[k] for group in self._COLUMNS for k in group], num_bold
        )

        sheet.set_column(0, 0, 42)
        sheet.set_column(1, 9, 15)
