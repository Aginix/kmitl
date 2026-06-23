# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.tools import format_date


class GeneralLedgerReportKmitl(models.AbstractModel):
    """General Ledger computed by the OCA engine, extended with KMITL
    accounting-dimension filtering and reshaped for an OWL client action.

    Per account: an opening balance, the period's move lines in date order
    (with a running balance) and a closing balance. The same compute
    (:meth:`get_general_ledger_data`) feeds the on-screen OWL client action
    (called over RPC), the QWeb PDF and the XLSX export, so all three agree.

    Unlike the Trial Balance -- which has to override the OCA domain builders
    because its ``_get_data`` takes no extra-domain argument -- the General
    Ledger engine threads an ``extra_domain`` through both the initial-balance
    and period queries, so the KMITL dimension leaves are injected there.
    """

    _name = "report.accounting_kmitl_reports.general_ledger_kmitl"
    _description = "KMITL General Ledger Report"
    _inherit = [
        "report.account_financial_report.general_ledger",
        "accounting_kmitl_reports.dimension.filter.mixin",
    ]

    # ------------------------------------------------------------------
    # Shared compute
    # ------------------------------------------------------------------
    @api.model
    def get_general_ledger_data(self, options):
        """Compute the general ledger for ``options`` and return JSON-friendly
        accounts (each with its move lines). Called over RPC by the OWL client
        action and internally by the QWeb/XLSX reports.

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

        if not date_from or not date_to:
            return {"accounts": [], "currency_id": company.currency_id.id}

        only_posted = bool(options.get("only_posted", True))
        hide_at_0 = bool(options.get("hide_account_at_0", True))
        journal_ids = options.get("journal_ids") or []
        partner_ids = options.get("partner_ids") or []
        account_ids = list(options.get("account_ids") or [])
        account_ids = self._kmitl_apply_account_range(options, company_id, account_ids)

        # KMITL dimensions (and the optional journal filter) ride along on the
        # engine's extra_domain, which is AND-ed into every move-line query.
        extra_domain = list(self._kmitl_build_dim_leaves(options.get("dims") or {}))
        if journal_ids:
            extra_domain += [("journal_id", "in", journal_ids)]

        fy_start_date = self._kmitl_fy_start_date(date_from, company)

        # Same orchestration as the OCA ``_get_report_values`` (single company,
        # no foreign currency, no centralization, ungrouped lines).
        gen_ld_data = self._get_initial_balance_data(
            account_ids,
            partner_ids,
            company_id,
            date_from,
            False,  # foreign_currency
            only_posted,
            False,  # unaffected_earnings_account
            fy_start_date,
            [],  # cost_center_ids (KMITL dims travel through extra_domain)
            extra_domain,
            "none",  # grouped_by
        )
        (
            gen_ld_data,
            accounts_data,
            journals_data,
            _full_reconcile_data,
            _taxes_data,
            _analytic_data,
            rec_after_date_to_ids,
        ) = self._get_period_ml_data(
            account_ids,
            partner_ids,
            company_id,
            False,  # foreign_currency
            only_posted,
            date_from,
            date_to,
            gen_ld_data,
            [],  # cost_center_ids
            extra_domain,
            "none",  # grouped_by
        )
        general_ledger = self._create_general_ledger(
            gen_ld_data, accounts_data, "none", rec_after_date_to_ids, hide_at_0
        )
        general_ledger = sorted(general_ledger, key=lambda a: a["code"] or "")

        accounts = []
        for acc in general_ledger:
            lines = []
            for ml in acc.get("move_lines", []):
                journal = journals_data.get(ml["journal_id"], {}) if ml.get(
                    "journal_id"
                ) else {}
                lines.append(
                    {
                        "id": ml["id"],
                        "date": fields.Date.to_string(ml["date"]) if ml["date"] else "",
                        "entry": ml.get("entry") or "",
                        "entry_id": ml.get("entry_id") or False,
                        "journal": journal.get("code") or "",
                        "partner": ml.get("partner_name") or "",
                        "ref_label": ml.get("ref_label") or "",
                        "debit": ml.get("debit") or 0.0,
                        "credit": ml.get("credit") or 0.0,
                        "balance": ml.get("balance") or 0.0,
                    }
                )
            accounts.append(
                {
                    "id": acc["id"],
                    "code": acc["code"] or "",
                    "name": acc["name"] or "",
                    "initial_balance": acc["init_bal"]["balance"],
                    "final_debit": acc["fin_bal"]["debit"],
                    "final_credit": acc["fin_bal"]["credit"],
                    "final_balance": acc["fin_bal"]["balance"],
                    "lines": lines,
                }
            )
        return {"accounts": accounts, "currency_id": company.currency_id.id}

    @api.model
    def get_move_lines_detail(self, move_id):
        """Return the full debit/credit breakdown of a journal entry — every
        line of the ``account.move`` — for the General Ledger drill-down (the
        OWL ``expand`` on a ledger line). Access rules apply via the ORM."""
        move = self.env["account.move"].browse(move_id).exists()
        if not move:
            return {"name": "", "date": "", "journal": "", "lines": []}
        lines = []
        for ml in move.line_ids.sorted(key=lambda line: (line.account_id.code or "", line.id)):
            lines.append(
                {
                    "id": ml.id,
                    "account": "%s - %s"
                    % (ml.account_id.code or "", ml.account_id.name or ""),
                    "partner": ml.partner_id.display_name or "",
                    "label": ml.name or "",
                    "debit": ml.debit,
                    "credit": ml.credit,
                }
            )
        return {
            "name": move.name or "",
            "date": fields.Date.to_string(move.date) if move.date else "",
            "journal": move.journal_id.code or "",
            "lines": lines,
        }

    @api.model
    def _kmitl_format_amount(self, value):
        """Shared number formatting (kept identical to the OWL side so the PDF
        mirrors the screen). Blank for ~zero to reduce clutter."""
        if not value or abs(value) < 0.005:
            return ""
        return "{:,.2f}".format(value)

    # ------------------------------------------------------------------
    # PDF / XLSX export — return the report action so the OWL client action
    # can ``doAction`` it. Filters travel in ``data`` so the output mirrors the
    # on-screen report exactly (no persisted record needed).
    # ------------------------------------------------------------------
    def _kmitl_report_action(self, options, report_xmlid):
        options = options or {}
        carrier = self.env["general.ledger.report.wizard.kmitl"].create(
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
            options, "accounting_kmitl_reports.action_report_general_ledger_kmitl"
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options, "accounting_kmitl_reports.action_report_general_ledger_kmitl_xlsx"
        )

    # ------------------------------------------------------------------
    # QWeb PDF rendering — reuse the shared compute (do NOT call the OCA
    # ``_get_report_values``, which expects the column-based wizard data dict).
    # ------------------------------------------------------------------
    def _get_report_values(self, docids, data):
        data = data or {}
        options = data.get("options") or {}
        result = self.get_general_ledger_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": "general.ledger.report.wizard.kmitl",
            "docs": self.env["general.ledger.report.wizard.kmitl"].browse(docids or []),
            "res_company": company,
            "accounts": result["accounts"],
            "format_amount": self._kmitl_format_amount,
            "date_from_label": format_date(self.env, options.get("date_from")),
            "date_to_label": format_date(self.env, options.get("date_to")),
        }


class GeneralLedgerXlsxKmitl(models.AbstractModel):
    """XLSX export of the general ledger — shares the compute with the screen
    and the PDF, so all three stay in sync."""

    _name = "report.accounting_kmitl_reports.general_ledger_xlsx"
    _description = "KMITL General Ledger XLSX"
    _inherit = "report.report_xlsx.abstract"

    # Date | Entry | Journal | Partner | Label | Debit | Credit | Balance
    _AMOUNT_COLS = (5, 6, 7)

    def generate_xlsx_report(self, workbook, data, objs):
        data = data or {}
        options = data.get("options") or {}
        report = self.env["report.accounting_kmitl_reports.general_ledger_kmitl"]
        result = report.get_general_ledger_data(options)
        accounts = result["accounts"]
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet(_("General Ledger"))
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
        acc_fmt = workbook.add_format({"bold": True, "bg_color": "#F7F7F7"})
        cell = workbook.add_format({"border": 1})
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        num_bold = workbook.add_format(
            {"border": 1, "bold": True, "num_format": "#,##0.00"}
        )

        sheet.merge_range(0, 0, 0, 7, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 7, _("General Ledger"), bold)
        sheet.merge_range(
            2,
            0,
            2,
            7,
            "%s %s %s %s"
            % (
                _("From"),
                options.get("date_from") or "",
                _("to"),
                options.get("date_to") or "",
            ),
        )

        headers = [
            _("Date"),
            _("Entry"),
            _("Journal"),
            _("Partner"),
            _("Label"),
            _("Debit"),
            _("Credit"),
            _("Balance"),
        ]
        row_top = 4
        for col, label in enumerate(headers):
            sheet.write(row_top, col, label, head)

        def write_amounts(row_idx, values, fmt):
            for col, value in zip(self._AMOUNT_COLS, values):
                if not value or abs(value) < 0.005:
                    sheet.write_blank(row_idx, col, None, fmt)
                else:
                    sheet.write_number(row_idx, col, value, fmt)

        r = row_top + 1
        for acc in accounts:
            sheet.merge_range(
                r, 0, r, 7, "%s - %s" % (acc["code"], acc["name"]), acc_fmt
            )
            r += 1
            # Opening balance row
            sheet.write(r, 4, _("Opening Balance"), cell)
            write_amounts(r, [None, None, acc["initial_balance"]], num)
            r += 1
            for line in acc["lines"]:
                sheet.write(r, 0, line["date"], cell)
                sheet.write(r, 1, line["entry"], cell)
                sheet.write(r, 2, line["journal"], cell)
                sheet.write(r, 3, line["partner"], cell)
                sheet.write(r, 4, line["ref_label"], cell)
                write_amounts(r, [line["debit"], line["credit"], line["balance"]], num)
                r += 1
            # Closing balance row
            sheet.write(r, 4, _("Ending Balance"), num_bold)
            write_amounts(
                r,
                [acc["final_debit"], acc["final_credit"], acc["final_balance"]],
                num_bold,
            )
            r += 1

        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 18)
        sheet.set_column(2, 2, 12)
        sheet.set_column(3, 4, 30)
        sheet.set_column(5, 7, 15)
