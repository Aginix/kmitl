# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.tools import format_date, format_datetime, html2plaintext

_SKIP_DISPLAY_TYPES = ["line_section", "line_note"]


class GeneralJournalReportKmitl(models.AbstractModel):
    """General Journal (สมุดรายวันทั่วไป): every journal entry in the period,
    in date order, each expandable to its debit/credit detail lines.

    Computed directly over ``account.move`` (the KMITL accounting dimensions
    and the partner filter live on the entry's lines, so they are matched
    through ``line_ids``). The same compute (:meth:`get_general_journal_data`)
    feeds the on-screen OWL client action (over RPC), the QWeb PDF and the XLSX
    export, so all three always agree.
    """

    _name = "report.accounting_kmitl_reports.general_journal_kmitl"
    _description = "KMITL General Journal Report"
    _inherit = ["accounting_kmitl_reports.dimension.filter.mixin"]

    # ------------------------------------------------------------------
    # Shared compute
    # ------------------------------------------------------------------
    @api.model
    def get_general_journal_data(self, options, with_lines=False):
        """Compute the general journal for ``options`` and return JSON-friendly
        entries in date order. Called over RPC by the OWL client action
        (``with_lines=False``; the lines are fetched lazily on expand) and
        internally by the QWeb/XLSX reports (``with_lines=True``).

        ``options`` keys: ``company_id``, ``date_from``, ``date_to``,
        ``only_posted`` (bool), ``journal_ids``, ``partner_ids`` and ``dims``
        (``{code: [analytic_account_ids]}``).
        """
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        company = self.env["res.company"].browse(company_id)
        date_from = options.get("date_from")
        date_to = options.get("date_to")

        if not date_from or not date_to:
            return {"entries": [], "currency_id": company.currency_id.id}

        only_posted = bool(options.get("only_posted", True))
        journal_ids = options.get("journal_ids") or []
        partner_ids = options.get("partner_ids") or []

        # Entry domain. Dimensions/partner live on the lines, so they are
        # matched through ``line_ids`` (an entry qualifies if any line matches).
        domain = [
            ("company_id", "=", company_id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        domain.append(
            ("state", "=", "posted")
            if only_posted
            else ("state", "in", ["posted", "draft"])
        )
        if journal_ids:
            domain.append(("journal_id", "in", journal_ids))
        if partner_ids:
            domain.append(("line_ids.partner_id", "in", partner_ids))
        for field_name, op, value in self._kmitl_build_dim_leaves(
            options.get("dims") or {}, options.get("dim_only_self")
        ):
            domain.append(("line_ids." + field_name, op, value))

        # Newest entries first: by accounting date, then by record timestamp
        # (so the displayed date-time column reads newest → oldest).
        moves = self.env["account.move"].search(
            domain, order="date desc, create_date desc"
        )
        if not moves:
            return {"entries": [], "currency_id": company.currency_id.id}

        # Per-entry totals over its real posting lines (section/note excluded).
        totals = self.env["account.move.line"].read_group(
            [
                ("move_id", "in", moves.ids),
                ("display_type", "not in", _SKIP_DISPLAY_TYPES),
            ],
            ["debit:sum", "credit:sum"],
            ["move_id"],
            lazy=False,
        )
        totals_by_move = {
            g["move_id"][0]: (g.get("debit") or 0.0, g.get("credit") or 0.0)
            for g in totals
            if g.get("move_id")
        }
        lines_map = (
            self._kmitl_move_lines_detail(moves.ids) if with_lines else {}
        )
        has_submitted = "submitted_by" in self.env["account.move"]._fields

        entries = []
        for mv in moves:
            debit, credit = totals_by_move.get(mv.id, (0.0, 0.0))
            if has_submitted and mv.submitted_by:
                maker = mv.submitted_by.display_name
                mdate = mv.submitted_date or mv.date
            else:
                maker = mv.create_uid.display_name
                mdate = mv.create_date or mv.date
            entries.append(
                {
                    "id": mv.id,
                    # Date-time the entry was recorded, in the user's timezone,
                    # formatted as 25/06/2026 23:59:59.
                    "date": format_datetime(
                        self.env, mv.create_date, dt_format="dd/MM/yyyy HH:mm:ss"
                    )
                    if mv.create_date
                    else "",
                    "name": mv.name or "/",
                    "journal": mv.journal_id.code or mv.journal_id.name or "",
                    "ref": mv.ref or "",
                    "partner": mv.partner_id.display_name or "",
                    "state": mv.state,
                    "debit": debit,
                    "credit": credit,
                    "narration": html2plaintext(mv.narration) if mv.narration else "",
                    "maker": maker or "",
                    "maker_date": fields.Date.to_string(mdate) if mdate else "",
                    "lines": lines_map.get(mv.id, []),
                }
            )
        return {"entries": entries, "currency_id": company.currency_id.id}

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
        carrier = self.env["general.journal.report.wizard.kmitl"].create(
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
            options, "accounting_kmitl_reports.action_report_general_journal_kmitl"
        )

    @api.model
    def action_export_xlsx(self, options):
        return self._kmitl_report_action(
            options,
            "accounting_kmitl_reports.action_report_general_journal_kmitl_xlsx",
        )

    @api.model
    def action_export_csv(self, options):
        return self._kmitl_report_action(
            options,
            "accounting_kmitl_reports.action_report_general_journal_kmitl_csv",
        )

    # ------------------------------------------------------------------
    # QWeb PDF rendering — reuse the shared compute (with lines).
    # ------------------------------------------------------------------
    def _get_report_values(self, docids, data):
        data = data or {}
        options = data.get("options") or {}
        result = self.get_general_journal_data(options, with_lines=True)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": "general.journal.report.wizard.kmitl",
            "docs": self.env["general.journal.report.wizard.kmitl"].browse(
                docids or []
            ),
            "res_company": company,
            "entries": result["entries"],
            "format_amount": self._kmitl_format_amount,
            "date_from_label": format_date(self.env, options.get("date_from")),
            "date_to_label": format_date(self.env, options.get("date_to")),
        }


class GeneralJournalXlsxKmitl(models.AbstractModel):
    """XLSX export of the general journal — shares the compute with the screen
    and the PDF, so all three stay in sync."""

    _name = "report.accounting_kmitl_reports.general_journal_xlsx"
    _description = "KMITL General Journal XLSX"
    _inherit = "report.report_xlsx.abstract"

    # Date | Number | Journal | Account | Label | Dimensions | Debit | Credit
    _AMOUNT_COLS = (6, 7)

    def generate_xlsx_report(self, workbook, data, objs):
        data = data or {}
        options = data.get("options") or {}
        report = self.env["report.accounting_kmitl_reports.general_journal_kmitl"]
        result = report.get_general_journal_data(options, with_lines=True)
        entries = result["entries"]
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet(_("General Journal"))
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
        entry_fmt = workbook.add_format({"bold": True, "bg_color": "#F7F7F7"})
        entry_num = workbook.add_format(
            {"bold": True, "bg_color": "#F7F7F7", "num_format": "#,##0.00"}
        )
        cell = workbook.add_format({"border": 1})
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})

        sheet.merge_range(0, 0, 0, 7, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 7, _("General Journal"), bold)
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
            _("Date-Time"),
            _("Number"),
            _("Journal"),
            _("Account"),
            _("Label"),
            _("Dimensions"),
            _("Debit"),
            _("Credit"),
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
        for entry in entries:
            # Entry header row (date | number | journal | totals).
            sheet.write(r, 0, entry["date"], entry_fmt)
            sheet.write(r, 1, entry["name"], entry_fmt)
            sheet.write(r, 2, entry["journal"], entry_fmt)
            sheet.write(r, 3, "", entry_fmt)
            sheet.write(r, 4, entry["ref"], entry_fmt)
            sheet.write(r, 5, "", entry_fmt)
            write_amounts(r, [entry["debit"], entry["credit"]], entry_num)
            r += 1
            for line in entry["lines"]:
                sheet.write(r, 0, "", cell)
                sheet.write(r, 1, "", cell)
                sheet.write(r, 2, "", cell)
                sheet.write(r, 3, line["account"], cell)
                sheet.write(r, 4, line["label"], cell)
                sheet.write(r, 5, line["dim_text"], cell)
                write_amounts(r, [line["debit"], line["credit"]], num)
                r += 1

        sheet.set_column(0, 0, 18)
        sheet.set_column(1, 1, 18)
        sheet.set_column(2, 2, 12)
        sheet.set_column(3, 3, 32)
        sheet.set_column(4, 4, 32)
        sheet.set_column(5, 5, 30)
        sheet.set_column(6, 7, 15)


class GeneralJournalCsvKmitl(models.AbstractModel):
    """CSV export of the general journal — one flat row per posting line, with
    the entry context (date-time / number / journal / reference / partner)
    repeated on every row, so the file is ready for pivot/analysis. Shares the
    compute with the screen / PDF / XLSX."""

    _name = "report.accounting_kmitl_reports.general_journal_csv"
    _inherit = "accounting_kmitl_reports.csv.report"
    _description = "KMITL General Journal CSV"

    def _kmitl_csv_rows(self, options):
        report = self.env["report.accounting_kmitl_reports.general_journal_kmitl"]
        result = report.get_general_journal_data(options, with_lines=True)
        rows = [
            [
                _("Date-Time"),
                _("Number"),
                _("Journal"),
                _("Reference"),
                _("Partner"),
                _("Account"),
                _("Label"),
                _("Dimensions"),
                _("Debit"),
                _("Credit"),
            ]
        ]
        for entry in result["entries"]:
            for line in entry["lines"]:
                rows.append(
                    [
                        entry["date"],
                        entry["name"],
                        entry["journal"],
                        entry["ref"],
                        entry["partner"],
                        line["account"],
                        line["label"],
                        line["dim_text"],
                        self._csv_num(line["debit"]),
                        self._csv_num(line["credit"]),
                    ]
                )
        return rows
