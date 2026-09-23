# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from collections import defaultdict

from odoo import _, api, models
from odoo.tools import format_date
from odoo.tools.float_utils import float_is_zero

from .dimension_filter_mixin import SKIP_DISPLAY_TYPES


class TrialBalanceReportKmitl(models.AbstractModel):
    """Trial balance over ``account.move.line``, filtered by the KMITL
    accounting dimensions and laid out as Debit / Credit / Balance.

    The compute is ours rather than the OCA ``account_financial_report``
    engine's. Everything that engine adds on top of the three aggregations
    below -- partner details, foreign currency, account hierarchy, analytic
    grouping, unaffected earnings -- is switched off for KMITL, so inheriting
    it bought us no maintenance while coupling the report to a private method
    OCA reshapes between releases.

    The same compute (:meth:`get_trial_balance_data`) feeds the on-screen OWL
    client action (called over RPC), the QWeb PDF, the XLSX and the CSV, so
    every output mirrors the screen.
    """

    _name = "report.accounting_kmitl_reports.trial_balance_kmitl"
    _description = "KMITL Trial Balance Report"
    _inherit = "accounting_kmitl_reports.dimension.filter.mixin"

    # ------------------------------------------------------------------
    # Move-line domains
    #
    # KMITL dimensions live in ``account.move.line.analytic_distribution``
    # (a JSON of {analytic_account_id: percentage}); the mixin turns the
    # selection into domain leaves that are appended to every aggregation.
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_common_ml_domain(
        self, company_id, journal_ids, partner_ids, only_posted
    ):
        """The leaves shared by the opening-balance and period aggregations."""
        domain = [("company_id", "=", company_id)]
        if journal_ids:
            domain.append(("journal_id", "in", journal_ids))
        if partner_ids:
            domain.append(("partner_id", "in", partner_ids))
        if only_posted:
            domain.append(("move_id.state", "=", "posted"))
        else:
            domain.append(("move_id.state", "in", ["posted", "draft"]))
        return domain

    @api.model
    def _kmitl_accounts(self, company_id, account_ids, include_initial_balance=None):
        """The accounts to report on, optionally restricted to the
        balance-sheet ones (``include_initial_balance``) or the P&L ones."""
        domain = [("company_id", "=", company_id)]
        if account_ids:
            domain.append(("id", "in", account_ids))
        if include_initial_balance is not None:
            domain.append(("include_initial_balance", "=", include_initial_balance))
        return self.env["account.account"].search(domain)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.model
    def _kmitl_opening_balances(
        self, company_id, account_ids, common_domain, date_from, fy_start_date
    ):
        """``{account_id: opening balance}`` as of ``date_from``.

        Read in two passes because profit & loss accounts restart every
        fiscal year: balance-sheet accounts (``include_initial_balance``)
        accumulate every entry before ``date_from``, P&L accounts only the
        entries since ``fy_start_date``.
        """
        opening = defaultdict(float)
        for include_initial_balance in (True, False):
            accounts = self._kmitl_accounts(
                company_id, account_ids, include_initial_balance
            )
            if not accounts:
                continue
            domain = common_domain + [
                ("account_id", "in", accounts.ids),
                ("date", "<", date_from),
            ]
            if not include_initial_balance:
                domain.append(("date", ">=", fy_start_date))
            for group in self.env["account.move.line"].read_group(
                domain, ["balance"], ["account_id"]
            ):
                opening[group["account_id"][0]] += group["balance"] or 0.0
        return opening

    @api.model
    def _kmitl_account_totals(self, options, company):
        """``{account_id: {initial_balance, debit, credit, ending_balance}}``
        for every account in scope, seeded at zero so an account with no entry
        at all still shows up when "hide accounts at 0" is off."""
        company_id = company.id
        date_from = options["date_from"]
        journal_ids = options.get("journal_ids") or []
        partner_ids = options.get("partner_ids") or []
        account_ids = self._kmitl_apply_account_range(
            options, company_id, list(options.get("account_ids") or [])
        )
        common_domain = self._kmitl_common_ml_domain(
            company_id,
            journal_ids,
            partner_ids,
            bool(options.get("only_posted", True)),
        ) + self._kmitl_build_dim_leaves(
            options.get("dims") or {}, options.get("dim_only_self")
        )

        totals = {
            account.id: {
                "initial_balance": 0.0,
                "debit": 0.0,
                "credit": 0.0,
                "ending_balance": 0.0,
            }
            for account in self._kmitl_accounts(company_id, account_ids)
        }

        period_domain = common_domain + [
            ("display_type", "not in", SKIP_DISPLAY_TYPES),
            ("date", ">=", date_from),
            ("date", "<=", options["date_to"]),
        ]
        if account_ids:
            period_domain.append(("account_id", "in", account_ids))
        for group in self.env["account.move.line"].read_group(
            period_domain, ["debit", "credit", "balance"], ["account_id"]
        ):
            total = totals.get(group["account_id"][0])
            if total is None:
                continue
            total["debit"] = group["debit"] or 0.0
            total["credit"] = group["credit"] or 0.0
            total["ending_balance"] = group["balance"] or 0.0

        opening = self._kmitl_opening_balances(
            company_id,
            account_ids,
            common_domain,
            date_from,
            self._kmitl_fy_start_date(date_from, company),
        )
        for account_id, balance in opening.items():
            total = totals.get(account_id)
            if total is None:
                continue
            total["initial_balance"] = balance
            total["ending_balance"] += balance
        return totals

    @api.model
    def _kmitl_drop_accounts_at_0(self, totals, company):
        """Drop the accounts whose opening, movements and closing are all
        zero (the "hide accounts at 0" option)."""
        rounding = company.currency_id.rounding
        return {
            account_id: total
            for account_id, total in totals.items()
            if not all(
                float_is_zero(amount, precision_rounding=rounding)
                for amount in total.values()
            )
        }

    @api.model
    def get_trial_balance_data(self, options):
        """Compute the trial balance for ``options`` and return JSON-friendly
        rows. Called over RPC by the OWL client action and internally by the
        QWeb / XLSX / CSV reports.

        ``options`` keys: ``company_id``, ``date_from``, ``date_to``,
        ``only_posted`` (bool), ``hide_account_at_0`` (bool), ``journal_ids``,
        ``partner_ids``, ``account_ids``, ``account_code_from_id``,
        ``account_code_to_id`` and ``dims`` (``{code: [analytic_account_ids]}``).
        """
        options = options or {}
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        empty = {
            "rows": [],
            "totals": self._kmitl_empty_totals(),
            "currency_id": company.currency_id.id,
        }
        if not options.get("date_from") or not options.get("date_to"):
            return empty

        account_totals = self._kmitl_account_totals(options, company)
        if bool(options.get("hide_account_at_0", True)):
            account_totals = self._kmitl_drop_accounts_at_0(account_totals, company)

        rows = []
        totals = self._kmitl_empty_totals()
        accounts = self.env["account.account"].browse(list(account_totals))
        for account in accounts.sorted(lambda a: a.code or ""):
            amounts = account_totals[account.id]
            opening = amounts["initial_balance"]
            debit = amounts["debit"]
            credit = amounts["credit"]
            ending = amounts["ending_balance"]
            row = {
                "id": account.id,
                "code": account.code or "",
                "name": account.name or "",
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

    @api.model
    def _kmitl_format_total(self, value):
        """Like :meth:`_kmitl_format_amount` but renders an exact zero as
        ``0.00`` — used by the totals row."""
        return "{:,.2f}".format(value or 0.0)

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

    @api.model
    def action_export_csv(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_trial_balance_kmitl_csv"
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
            "format_total": self._kmitl_format_total,
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

        def write_amounts(row_idx, values, fmt, blank_zero=True):
            for col, value in enumerate(values, start=1):
                if blank_zero and (not value or abs(value) < 0.005):
                    sheet.write_blank(row_idx, col, None, fmt)
                else:
                    sheet.write_number(row_idx, col, value or 0.0, fmt)

        r = row_top + 2
        for row in rows:
            sheet.write(r, 0, "%s - %s" % (row["code"], row["name"]), cell)
            write_amounts(
                r, [row[k] for group in self._COLUMNS for k in group], num
            )
            r += 1

        sheet.write(r, 0, _("Total"), num_bold)
        write_amounts(
            r,
            [totals[k] for group in self._COLUMNS for k in group],
            num_bold,
            blank_zero=False,
        )

        sheet.set_column(0, 0, 42)
        sheet.set_column(1, 9, 15)


class TrialBalanceCsvKmitl(models.AbstractModel):
    """CSV export of the trial balance — one flat row per account (no
    subtotals), sharing the compute with the screen / PDF / XLSX."""

    _name = "report.accounting_kmitl_reports.trial_balance_csv"
    _inherit = "accounting_kmitl_reports.csv.report"
    _description = "KMITL Trial Balance CSV"

    _COLS = (
        "opening_debit",
        "opening_credit",
        "opening_balance",
        "period_debit",
        "period_credit",
        "period_balance",
        "ending_debit",
        "ending_credit",
        "ending_balance",
    )

    def _kmitl_csv_rows(self, options):
        report = self.env["report.accounting_kmitl_reports.trial_balance_kmitl"]
        result = report.get_trial_balance_data(options)
        rows = [
            [
                _("Account Code"),
                _("Account Name"),
                _("Opening Debit"),
                _("Opening Credit"),
                _("Opening Balance"),
                _("Period Debit"),
                _("Period Credit"),
                _("Period Balance"),
                _("Ending Debit"),
                _("Ending Credit"),
                _("Ending Balance"),
            ]
        ]
        for row in result["rows"]:
            rows.append(
                [row["code"], row["name"]]
                + [self._csv_num(row[k]) for k in self._COLS]
            )
        return rows
