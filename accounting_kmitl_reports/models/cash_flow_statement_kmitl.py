# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, models
from odoo.tools import format_date

# ---------------------------------------------------------------------------
# Cash-flow activity classification by ``account_type`` (Odoo 16).
#
# The statement is built with the indirect / balance-variation method: because
# every entry is balanced (debit == credit), the period change in cash equals
# the *negative* of the period movement of every non-cash account. So each
# activity's cash flow is ``-(sum of debit - credit)`` of the accounts assigned
# to it, and -- as long as every on-balance, non-cash account type is assigned
# to exactly one activity -- the three activities net to the change in cash.
#
# Note on precision: classifying purely by ``account_type`` keeps the *net*
# change exact, but does not add depreciation back across activities
# (``expense_depreciation`` sits in operating while the matching accumulated
# depreciation sits in investing), so the operating/investing split of
# depreciation is approximate. ``off_balance`` is excluded (no cash effect).
# ---------------------------------------------------------------------------
PL_TYPES = (
    "income",
    "income_other",
    "expense",
    "expense_depreciation",
    "expense_direct_cost",
)
OPERATING_BS_TYPES = (
    "asset_receivable",
    "asset_current",
    "asset_prepayments",
    "liability_payable",
    "liability_current",
)
INVESTING_TYPES = ("asset_fixed", "asset_non_current")
FINANCING_TYPES = (
    "liability_non_current",
    "liability_credit_card",
    "equity",
    "equity_unaffected",
)
CASH_TYPES = ("asset_cash",)

# Every non-cash account type that participates in an activity.
ACTIVITY_TYPES = PL_TYPES + OPERATING_BS_TYPES + INVESTING_TYPES + FINANCING_TYPES


class CashFlowReportKmitl(models.AbstractModel):
    """Cash Flow Statement computed over the ``account.move.line`` ledger with
    the indirect / balance-variation method, extended with KMITL
    accounting-dimension filtering.

    The same compute (:meth:`get_cash_flow_data`) feeds the on-screen OWL client
    action (over RPC), the QWeb PDF and the XLSX export, so all three always
    agree.
    """

    _name = "report.accounting_kmitl_reports.cash_flow_kmitl"
    _description = "KMITL Cash Flow Statement Report"
    _inherit = ["accounting_kmitl_reports.dimension.filter.mixin"]

    # ------------------------------------------------------------------
    # Shared compute
    # ------------------------------------------------------------------
    @api.model
    def get_cash_flow_data(self, options):
        """Compute the cash flow statement for ``options`` and return
        JSON-friendly rows + a summary. Called over RPC by the OWL client
        action and internally by the QWeb/XLSX reports.

        ``options`` keys: ``company_id``, ``date_from``, ``date_to``,
        ``only_posted`` (bool), ``hide_account_at_0`` (bool) and ``dims``
        (``{code: [analytic_account_ids]}``).
        """
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        date_from = options.get("date_from")
        date_to = options.get("date_to")

        if not date_from or not date_to:
            return {
                "rows": [],
                "summary": self._kmitl_empty_summary(),
                "currency_id": company.currency_id.id,
            }

        only_posted = bool(options.get("only_posted", True))
        hide_at_0 = bool(options.get("hide_account_at_0", True))
        leaves = self._kmitl_build_dim_leaves(
            options.get("dims") or {}, options.get("dim_only_self")
        )
        # Posted only, or every non-cancelled entry (posted + draft).
        state_leaf = (
            [("parent_state", "=", "posted")]
            if only_posted
            else [("parent_state", "!=", "cancel")]
        )

        # One pass over the period for every classified (non-cash) account.
        period_domain = (
            [
                ("company_id", "=", company_id),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("account_id.account_type", "in", list(ACTIVITY_TYPES)),
            ]
            + state_leaf
            + leaves
        )
        aml = self.env["account.move.line"]
        groups = aml.read_group(period_domain, ["balance:sum"], ["account_id"])
        # Per-account cash flow contribution = -(debit - credit) = -balance.
        by_account = {}
        for g in groups:
            acc = g["account_id"]
            if acc:
                by_account[acc[0]] = -(g.get("balance") or 0.0)

        accounts = self.env["account.account"].browse(list(by_account)).exists()
        acc_info = {
            a.id: (a.code or "", a.name or "", a.account_type) for a in accounts
        }

        def bucket(types):
            """Detail rows (hiding ~zero accounts when requested) and the full
            total for the accounts whose type is in ``types``."""
            details = []
            total = 0.0
            for acc_id, amount in by_account.items():
                code, name, atype = acc_info.get(acc_id, ("", "", False))
                if atype not in types:
                    continue
                total += amount
                if hide_at_0 and abs(amount) < 0.005:
                    continue
                details.append(
                    {"id": acc_id, "code": code, "name": name, "amount": amount}
                )
            details.sort(key=lambda r: r["code"])
            return details, total

        pl_details, net_profit = bucket(PL_TYPES)
        wc_details, wc_change = bucket(OPERATING_BS_TYPES)
        inv_details, cfi = bucket(INVESTING_TYPES)
        fin_details, cff = bucket(FINANCING_TYPES)
        cfo = net_profit + wc_change

        # Opening cash: balance of cash accounts accumulated before the period.
        cash_domain = (
            [
                ("company_id", "=", company_id),
                ("date", "<", date_from),
                ("account_id.account_type", "in", list(CASH_TYPES)),
            ]
            + state_leaf
            + leaves
        )
        cash_grp = aml.read_group(cash_domain, ["balance:sum"], [])
        cash_start = (cash_grp and cash_grp[0].get("balance")) or 0.0

        net_change = cfo + cfi + cff
        cash_end = cash_start + net_change

        rows = []
        rows.append(self._kmitl_row("section", _("Operating Activities")))
        rows.append(self._kmitl_row("group", _("Net profit (loss)"), amount=net_profit))
        rows += [dict(r, level="detail", label="") for r in pl_details]
        rows.append(
            self._kmitl_row(
                "group",
                _("Changes in operating assets and liabilities"),
                amount=wc_change,
            )
        )
        rows += [dict(r, level="detail", label="") for r in wc_details]
        rows.append(
            self._kmitl_row(
                "total", _("Net cash from operating activities"), amount=cfo
            )
        )

        rows.append(self._kmitl_row("section", _("Investing Activities")))
        rows += [dict(r, level="detail", label="") for r in inv_details]
        rows.append(
            self._kmitl_row(
                "total", _("Net cash from investing activities"), amount=cfi
            )
        )

        rows.append(self._kmitl_row("section", _("Financing Activities")))
        rows += [dict(r, level="detail", label="") for r in fin_details]
        rows.append(
            self._kmitl_row(
                "total", _("Net cash from financing activities"), amount=cff
            )
        )

        rows.append(
            self._kmitl_row(
                "grand_total", _("Net increase (decrease) in cash"), amount=net_change
            )
        )
        rows.append(
            self._kmitl_row("summary", _("Cash at beginning of period"), amount=cash_start)
        )
        rows.append(self._kmitl_row("summary", _("Cash at end of period"), amount=cash_end))

        summary = {
            "operating": cfo,
            "investing": cfi,
            "financing": cff,
            "net_change": net_change,
            "cash_start": cash_start,
            "cash_end": cash_end,
        }
        return {
            "rows": rows,
            "summary": summary,
            "currency_id": company.currency_id.id,
        }

    @api.model
    def _kmitl_row(self, level, label, amount=None):
        """A non-detail report row (section header, group, total or summary).
        ``amount`` is ``None`` for plain headers so the figure column stays
        blank."""
        return {
            "level": level,
            "label": label,
            "code": "",
            "name": "",
            "amount": amount,
        }

    @api.model
    def _kmitl_empty_summary(self):
        return {
            "operating": 0.0,
            "investing": 0.0,
            "financing": 0.0,
            "net_change": 0.0,
            "cash_start": 0.0,
            "cash_end": 0.0,
        }

    @api.model
    def _kmitl_format_amount(self, value):
        """Shared number formatting (kept identical to the OWL side so the PDF
        mirrors the screen). Blank for header rows (``None``)."""
        if value is None:
            return ""
        return "{:,.2f}".format(value)

    # ------------------------------------------------------------------
    # PDF / XLSX export — return the report action so the OWL client action
    # can ``doAction`` it. Filters travel in ``data`` so the output mirrors the
    # on-screen report exactly (no persisted record needed).
    # ------------------------------------------------------------------
    def _kmitl_report_action(self, options, report_xmlid):
        options = options or {}
        carrier = self.env["cash.flow.report.wizard.kmitl"].create(
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
            options, "accounting_kmitl_reports.action_report_cash_flow_kmitl"
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_cash_flow_kmitl_xlsx"
        )

    # ------------------------------------------------------------------
    # QWeb PDF rendering — reuse the shared compute.
    # ------------------------------------------------------------------
    def _get_report_values(self, docids, data):
        data = data or {}
        options = data.get("options") or {}
        result = self.get_cash_flow_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": "cash.flow.report.wizard.kmitl",
            "docs": self.env["cash.flow.report.wizard.kmitl"].browse(docids or []),
            "res_company": company,
            "rows": result["rows"],
            "summary": result["summary"],
            "format_amount": self._kmitl_format_amount,
            "date_from_label": format_date(self.env, options.get("date_from")),
            "date_to_label": format_date(self.env, options.get("date_to")),
        }


class CashFlowXlsxKmitl(models.AbstractModel):
    """XLSX export of the cash flow statement — shares the compute with the
    screen and the PDF, so all three stay in sync."""

    _name = "report.accounting_kmitl_reports.cash_flow_xlsx"
    _description = "KMITL Cash Flow Statement XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        data = data or {}
        options = data.get("options") or {}
        report = self.env["report.accounting_kmitl_reports.cash_flow_kmitl"]
        result = report.get_cash_flow_data(options)
        rows = result["rows"]
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet(_("Cash Flow Statement"))
        bold = workbook.add_format({"bold": True})
        num = workbook.add_format({"num_format": "#,##0.00"})
        num_bold = workbook.add_format({"bold": True, "num_format": "#,##0.00"})

        # Per-level label formatting (indent + weight); the figure column reuses
        # the bold/plain number formats.
        label_fmt = {
            "section": workbook.add_format({"bold": True}),
            "group": workbook.add_format({"italic": True, "indent": 1}),
            "detail": workbook.add_format({"indent": 2}),
            "total": workbook.add_format({"bold": True, "indent": 1}),
            "grand_total": workbook.add_format({"bold": True, "top": 1}),
            "summary": workbook.add_format({"bold": True}),
        }
        bold_levels = {"section", "total", "grand_total", "summary"}

        sheet.merge_range(0, 0, 0, 1, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 1, _("Cash Flow Statement"), bold)
        sheet.merge_range(
            2,
            0,
            2,
            1,
            "%s %s %s %s"
            % (
                _("From"),
                options.get("date_from") or "",
                _("to"),
                options.get("date_to") or "",
            ),
        )

        r = 4
        for row in rows:
            level = row["level"]
            label = row["label"] or (
                "%s - %s" % (row["code"], row["name"]) if row["code"] else ""
            )
            sheet.write(r, 0, label, label_fmt.get(level))
            amount = row["amount"]
            if amount is not None:
                sheet.write_number(
                    r, 1, amount, num_bold if level in bold_levels else num
                )
            r += 1

        sheet.set_column(0, 0, 52)
        sheet.set_column(1, 1, 18)
