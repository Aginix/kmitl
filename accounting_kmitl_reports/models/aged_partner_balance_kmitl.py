# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.tools import format_date

# Aging buckets, in display order. ``residual`` is the row total.
BUCKETS = ("current", "30_days", "60_days", "90_days", "120_days", "older")
# Map the menu's account type to the chart-of-accounts ``account_type``.
ACCOUNT_TYPE_MAP = {
    "receivable": "asset_receivable",
    "payable": "liability_payable",
}


class AgedPartnerBalanceKmitl(models.AbstractModel):
    """Aged Partner Balance computed by the OCA engine, extended with KMITL
    accounting-dimension filtering.

    The same compute (:meth:`get_aged_partner_data`) feeds the on-screen OWL
    client action (called over RPC), the QWeb PDF and the XLSX export, so all
    three always agree. Uses the standard fixed buckets (current / 1-30 / 31-60
    / 61-90 / 91-120 / 120+ days) — no configurable interval is exposed.
    """

    _name = "report.accounting_kmitl_reports.aged_partner_balance_kmitl"
    _description = "KMITL Aged Partner Balance Report"
    _inherit = [
        "report.account_financial_report.aged_partner_balance",
        "accounting_kmitl_reports.dimension.filter.mixin",
    ]

    # ------------------------------------------------------------------
    # Dimension filtering
    #
    # The receivable/payable control line usually carries no
    # ``analytic_distribution`` (the KMITL dimensions live on the invoice's
    # income/expense lines). So we resolve the selected dimensions to the set
    # of moves that carry them, and restrict the aged move lines to those
    # moves via a ``move_id`` leaf passed through the context.
    # ------------------------------------------------------------------
    @api.model
    def _get_move_lines_domain_not_reconciled(self, *args, **kwargs):
        domain = super()._get_move_lines_domain_not_reconciled(*args, **kwargs)
        return domain + self._kmitl_move_leaf()

    @api.model
    def _get_new_move_lines_domain(self, *args, **kwargs):
        domain = super()._get_new_move_lines_domain(*args, **kwargs)
        return domain + self._kmitl_move_leaf()

    def _kmitl_move_leaf(self):
        move_ids = self.env.context.get("kmitl_move_ids")
        if move_ids is None:
            return []
        return [("move_id", "in", move_ids)]

    @api.model
    def _kmitl_accounts_for_type(self, account_type, company_id):
        at = ACCOUNT_TYPE_MAP.get(account_type)
        if not at:
            return []
        return (
            self.env["account.account"]
            .search([("company_id", "=", company_id), ("account_type", "=", at)])
            .ids
        )

    # ------------------------------------------------------------------
    # Shared compute
    # ------------------------------------------------------------------
    @api.model
    def get_aged_partner_data(self, options):
        """Compute the aged partner balance for ``options`` and return
        JSON-friendly rows. Called over RPC by the OWL client action and
        internally by the QWeb / XLSX reports.

        ``options`` keys: ``company_id``, ``date_at`` (as-of date),
        ``date_from`` (optional), ``only_posted`` (bool), ``account_type``
        (``"receivable"``/``"payable"``), ``partner_ids``, ``account_ids``
        (optional override), ``show_move_line_details`` (bool) and ``dims``
        (``{code: [analytic_account_ids]}``).
        """
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        date_at = options.get("date_at")

        empty = {
            "accounts": [],
            "totals": self._kmitl_empty_buckets(),
            "currency_id": company.currency_id.id,
        }
        if not date_at:
            return empty

        account_type = options.get("account_type") or "receivable"
        only_posted = bool(options.get("only_posted", True))
        show_details = bool(options.get("show_move_line_details"))
        partner_ids = options.get("partner_ids") or []
        account_ids = list(options.get("account_ids") or [])
        if not account_ids:
            account_ids = self._kmitl_accounts_for_type(account_type, company_id)
        if not account_ids:
            return empty

        # Resolve the selected dimensions to the moves that carry them.
        move_ids = None
        leaves = self._kmitl_build_dim_leaves(options.get("dims") or {})
        if leaves:
            move_ids = self.env["account.move.line"].search(leaves).move_id.ids

        date_at_object = fields.Date.to_date(date_at)
        report = self.with_context(
            kmitl_move_ids=move_ids,
            # No interval configuration: the OCA engine then only fills the
            # fixed buckets, which is what we render.
            age_partner_config=self.env["account.age.report.configuration"].browse(),
        )
        (
            ag_pb_data,
            accounts_data,
            partners_data,
            journals_data,
        ) = report._get_move_lines_data(
            company_id,
            account_ids,
            partner_ids,
            date_at_object,
            options.get("date_from") or False,
            only_posted,
            show_details,
        )
        aged = report._create_account_list(
            ag_pb_data,
            accounts_data,
            partners_data,
            journals_data,
            show_details,
            date_at_object,
        )

        accounts = []
        totals = self._kmitl_empty_buckets()
        for acc in aged:
            partners = []
            for prt in acc["partners"]:
                prow = {"name": prt["name"] or _("Unknown")}
                prow.update({k: prt[k] for k in ("residual",) + BUCKETS})
                if show_details:
                    prow["move_lines"] = [
                        self._kmitl_format_move_line(ml) for ml in prt["move_lines"]
                    ]
                partners.append(prow)
            arow = {
                "id": acc["id"],
                "code": acc["code"] or "",
                "name": acc["name"] or "",
                "partners": partners,
            }
            arow.update({k: acc[k] for k in ("residual",) + BUCKETS})
            accounts.append(arow)
            for key in totals:
                totals[key] += acc[key]
        return {
            "accounts": accounts,
            "totals": totals,
            "currency_id": company.currency_id.id,
        }

    @api.model
    def _kmitl_format_move_line(self, ml):
        row = {
            "date": fields.Date.to_string(ml["date"]) or "",
            "due_date": fields.Date.to_string(ml["due_date"]) or "",
            "entry": ml["entry"] or "",
            "journal": ml["journal"] or "",
            "ref_label": ml["ref_label"] or "",
        }
        row.update({k: ml[k] for k in ("residual",) + BUCKETS})
        return row

    @api.model
    def _kmitl_empty_buckets(self):
        return {key: 0.0 for key in ("residual",) + BUCKETS}

    @api.model
    def _kmitl_report_title(self, account_type):
        if account_type == "payable":
            return _("Aged Payable")
        return _("Aged Receivable")

    @api.model
    def _kmitl_format_amount(self, value):
        """Shared number formatting (kept identical to the OWL side so the PDF
        mirrors the screen). Blank for ~zero to reduce clutter."""
        if not value or abs(value) < 0.005:
            return ""
        return "{:,.2f}".format(value)

    # ------------------------------------------------------------------
    # PDF / XLSX export — return the report action so the OWL client action
    # can ``doAction`` it. Filters travel in ``data`` so the output mirrors
    # the on-screen report exactly (no persisted record needed).
    # ------------------------------------------------------------------
    def _kmitl_report_action(self, options, report_xmlid):
        options = options or {}
        carrier = self.env["aged.partner.report.wizard.kmitl"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "date_at": options.get("date_at"),
            }
        )
        report = self.env.ref(report_xmlid)
        return report.report_action(carrier, data={"options": options})

    @api.model
    def action_print_pdf(self, options):
        return self._kmitl_report_action(
            options,
            "accounting_kmitl_reports.action_report_aged_partner_balance_kmitl",
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options,
            "accounting_kmitl_reports.action_report_aged_partner_balance_kmitl_xlsx",
        )

    # ------------------------------------------------------------------
    # QWeb PDF rendering — reuse the shared compute.
    # ------------------------------------------------------------------
    def _get_report_values(self, docids, data):
        data = data or {}
        options = data.get("options") or {}
        result = self.get_aged_partner_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": "aged.partner.report.wizard.kmitl",
            "docs": self.env["aged.partner.report.wizard.kmitl"].browse(docids or []),
            "res_company": company,
            "accounts": result["accounts"],
            "totals": result["totals"],
            "report_title": self._kmitl_report_title(options.get("account_type")),
            "format_amount": self._kmitl_format_amount,
            "date_at_label": format_date(self.env, options.get("date_at")),
        }


class AgedPartnerBalanceXlsxKmitl(models.AbstractModel):
    """XLSX export of the aged partner balance — shares the compute with the
    screen and the PDF, so all three stay in sync."""

    _name = "report.accounting_kmitl_reports.aged_partner_balance_xlsx"
    _description = "KMITL Aged Partner Balance XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        data = data or {}
        options = data.get("options") or {}
        report = self.env[
            "report.accounting_kmitl_reports.aged_partner_balance_kmitl"
        ]
        result = report.get_aged_partner_data(options)
        accounts = result["accounts"]
        totals = result["totals"]
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        title = report._kmitl_report_title(options.get("account_type"))

        sheet = workbook.add_worksheet(title)
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
        cell_bold = workbook.add_format({"border": 1, "bold": True})
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        num_bold = workbook.add_format(
            {"border": 1, "bold": True, "num_format": "#,##0.00"}
        )

        last_col = 1 + len(BUCKETS) + 1  # name + total + buckets
        sheet.merge_range(0, 0, 0, last_col, company.display_name, bold)
        sheet.merge_range(1, 0, 1, last_col, title, bold)
        sheet.merge_range(
            2,
            0,
            2,
            last_col,
            "%s %s" % (_("As of"), options.get("date_at") or ""),
        )

        labels = [
            _("Partner"),
            _("Total"),
            _("Current"),
            _("1-30"),
            _("31-60"),
            _("61-90"),
            _("91-120"),
            _("120+"),
        ]
        row_top = 4
        for col, label in enumerate(labels):
            sheet.write(row_top, col, label, head)

        keys = ("residual",) + BUCKETS

        def write_amounts(row_idx, source, fmt):
            for col, key in enumerate(keys, start=1):
                value = source[key]
                if not value or abs(value) < 0.005:
                    sheet.write_blank(row_idx, col, None, fmt)
                else:
                    sheet.write_number(row_idx, col, value, fmt)

        r = row_top + 1
        for account in accounts:
            sheet.write(
                r, 0, "%s - %s" % (account["code"], account["name"]), cell_bold
            )
            write_amounts(r, account, num_bold)
            r += 1
            for partner in account["partners"]:
                sheet.write(r, 0, "    %s" % partner["name"], cell)
                write_amounts(r, partner, num)
                r += 1

        sheet.write(r, 0, _("Total"), num_bold)
        write_amounts(r, totals, num_bold)

        sheet.set_column(0, 0, 42)
        sheet.set_column(1, last_col, 15)
