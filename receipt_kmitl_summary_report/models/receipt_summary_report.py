# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models

DIMENSION_FIELDS = [
    ("department_analytic_id", "departments"),
    ("fund_analytic_id", "funds"),
    ("source_analytic_id", "sources"),
    ("activity_analytic_id", "activities"),
    ("kmitl_project_analytic_id", "kmitl_project"),
    ("procurement_plan_analytic_id", "procurement_plan"),
]


def _payment_type_labels():
    return {
        "cash": _("Cash"),
        "cheque": _("Cheque"),
        "transfer": _("Transfer"),
    }


class ReceiptReport(models.AbstractModel):
    _name = "receipt_kmitl.receipt.report"
    _inherit = "accounting_kmitl_reports.dimension.filter.mixin"
    _description = "Receipt Report Data Provider"

    @api.model
    def get_report_data(self, options):
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        remittance_id = options.get("remittance_id")
        date_from = options.get("date_from")
        date_to = options.get("date_to")

        domain = [("company_id", "=", company_id)]
        if remittance_id:
            # Scoped to a single remittance — show all its receipts regardless
            # of date or state.
            domain.append(("remittance_id", "=", remittance_id))
        else:
            if not date_from or not date_to:
                return {"groups": [], "grand_total": 0}
            domain += [
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("state", "in", ["draft", "submitted", "approved", "done"]),
            ]

        payment_type = options.get("payment_type")
        if payment_type:
            domain.append(("payment_type", "=", payment_type))

        domain += self._kmitl_build_dim_leaves(options.get("dims"))

        receipts = self.env["kmitl.receipt"].search(
            domain, order="date desc, id desc"
        )

        rows = []
        for r in receipts:
            dim_parts = []
            for field_name, _code in DIMENSION_FIELDS:
                account = r[field_name]
                if account:
                    dim_parts.append(account.display_name)

            payment_extras = []
            if r.payment_type == "cheque":
                if r.cheque_number:
                    payment_extras.append("เลขที่เช็ค: %s" % r.cheque_number)
                if r.cheque_date:
                    payment_extras.append("วันที่เช็ค: %s" % r.cheque_date)
            elif r.payment_type == "transfer":
                if r.transfer_date:
                    payment_extras.append("วันที่โอนเงิน: %s" % r.transfer_date)

            rows.append({
                "id": r.id,
                "date": str(r.date),
                "name": r.name or "/",
                "description": r.description or "",
                "lines": [
                    {"name": l.name or "", "amount": l.amount or 0.0}
                    for l in r.line_ids
                ],
                "amount_total": r.amount_total,
                "dimensions": "\n".join(dim_parts),
                "note": r.note or "",
                "state": r.state,
                "customer_name": r.customer_name or "",
                "payment_type": r.payment_type or "",
                "payment_type_label": (
                    _payment_type_labels().get(r.payment_type, "")
                    if r.payment_type else ""
                ),
                "payment_method": (
                    r.payment_method_id.name if r.payment_method_id else ""
                ),
                "payment_extras": payment_extras,
                "user_name": r.user_id.name if r.user_id else "",
            })

        groups = {}
        for row in rows:
            groups.setdefault(row["date"], []).append(row)

        group_list = []
        for date in sorted(groups.keys(), reverse=True):
            group_rows = groups[date]
            group_list.append({
                "date": date,
                "rows": group_rows,
                "total": sum(r["amount_total"] for r in group_rows),
            })

        grand_total = sum(g["total"] for g in group_list)

        return {
            "groups": group_list,
            "grand_total": grand_total,
        }

    @api.model
    def action_export_xlsx(self, options):
        options = options or {}
        carrier = self.env["receipt_kmitl.report.wizard"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "date_from": options.get("date_from"),
                "date_to": options.get("date_to"),
            }
        )
        report = self.env.ref(
            "receipt_kmitl_summary_report.action_report_receipt_summary_xlsx"
        )
        return report.report_action(carrier, data={"options": options})

    @api.model
    def action_print_pdf(self, options):
        options = options or {}
        carrier = self.env["receipt_kmitl.report.wizard"].create(
            {
                "company_id": options.get("company_id") or self.env.company.id,
                "date_from": options.get("date_from"),
                "date_to": options.get("date_to"),
            }
        )
        report = self.env.ref(
            "receipt_kmitl_summary_report.action_report_receipt_summary_pdf"
        )
        return report.report_action(carrier, data={"options": options})

    @api.model
    def format_amount(self, value):
        if not value or abs(value) < 0.005:
            return ""
        return "{:,.2f}".format(value)

    @api.model
    def get_filter_lines(self, options):
        """Human-readable summary of the applied filters, for the PDF header."""
        options = options or {}
        lines = []
        remittance_name = options.get("remittance_name")
        if remittance_name:
            lines.append(_("Remittance: %s") % remittance_name)

        date_from = options.get("date_from")
        date_to = options.get("date_to")
        if date_from and date_to:
            lines.append(
                _("Period: %(date_from)s to %(date_to)s")
                % {"date_from": date_from, "date_to": date_to}
            )

        payment_type = options.get("payment_type")
        if payment_type:
            lines.append(
                _("Payment Type: %s")
                % _payment_type_labels().get(payment_type, payment_type)
            )

        dims = options.get("dims") or {}
        dim_titles = {
            "departments": _("Departments"),
            "sources": _("Sources"),
            "funds": _("Funds"),
            "activities": _("Activities"),
        }
        Analytic = self.env["account.analytic.account"]
        for code, title in dim_titles.items():
            ids = dims.get(code) or []
            if ids:
                names = Analytic.browse(ids).mapped("display_name")
                lines.append("%s: %s" % (title, ", ".join(names)))
        return lines


class ReceiptReportWizard(models.TransientModel):
    _name = "receipt_kmitl.report.wizard"
    _description = "Receipt Report Carrier"

    company_id = fields.Many2one("res.company")
    date_from = fields.Date()
    date_to = fields.Date()


class ReceiptReportXlsx(models.AbstractModel):
    _name = "report.receipt_kmitl.receipt_summary_xlsx"
    _description = "Receipt Summary XLSX"
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, objs):
        options = (data or {}).get("options") or {}
        report = self.env["receipt_kmitl.receipt.report"]
        result = report.get_report_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )

        sheet = workbook.add_worksheet(_("Receipt Summary"))
        bold = workbook.add_format({"bold": True})
        head = workbook.add_format(
            {"bold": True, "bg_color": "#F0F0F0", "border": 1, "align": "center"}
        )
        group_fmt = workbook.add_format({"bold": True, "bg_color": "#F7F7F7"})
        group_num = workbook.add_format(
            {"bold": True, "bg_color": "#F7F7F7", "num_format": "#,##0.00"}
        )
        cell = workbook.add_format({"border": 1})
        num = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        wrap = workbook.add_format({"border": 1, "text_wrap": True})
        total_fmt = workbook.add_format({"bold": True, "num_format": "#,##0.00"})

        sheet.merge_range(0, 0, 0, 8, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 8, _("Receipt Summary Report"), bold)
        sheet.merge_range(
            2, 0, 2, 8,
            "%s %s %s %s" % (
                _("From"), options.get("date_from") or "",
                _("to"), options.get("date_to") or "",
            ),
        )

        headers = [
            _("Date"), _("Receipt No."), _("Customer Name"),
            _("Description"), _("Amount"),
            _("Payment Type"),
            _("Analytic Dimensions"), _("Note"),
            _("Issued By"),
        ]
        row = 4
        for col, label in enumerate(headers):
            sheet.write(row, col, label, head)

        format_amount = self.env["receipt_kmitl.receipt.report"].format_amount

        row = 5
        for group in result.get("groups", []):
            sheet.write(row, 0, group["date"], group_fmt)
            for col in range(1, 4):
                sheet.write(row, col, "", group_fmt)
            sheet.write_number(row, 4, group["total"], group_num)
            for col in range(5, 9):
                sheet.write(row, col, "", group_fmt)
            row += 1
            for r in group["rows"]:
                sheet.write(row, 0, "", cell)
                sheet.write(row, 1, r["name"], cell)
                sheet.write(row, 2, r["customer_name"], cell)
                details_parts = []
                if r["description"]:
                    details_parts.append(r["description"])
                if r["lines"]:
                    details_parts.append("รายการ")
                    for l in r["lines"]:
                        details_parts.append(
                            "• %s  %s บาท" % (l["name"], format_amount(l["amount"]))
                        )
                sheet.write(row, 3, "\n".join(details_parts), wrap)
                amt = r["amount_total"] or 0
                if abs(amt) >= 0.005:
                    sheet.write_number(row, 4, amt, num)
                else:
                    sheet.write_blank(row, 4, None, num)
                payment_parts = []
                if r["payment_type_label"]:
                    payment_parts.append(r["payment_type_label"])
                if r["payment_method"]:
                    payment_parts.append("วิธีชำระเงิน: %s" % r["payment_method"])
                for extra in r["payment_extras"]:
                    payment_parts.append("• %s" % extra)
                sheet.write(row, 5, "\n".join(payment_parts), wrap)
                sheet.write(row, 6, r["dimensions"], wrap)
                sheet.write(row, 7, r["note"], cell)
                sheet.write(row, 8, r["user_name"], cell)
                row += 1

        row += 1
        sheet.write(row, 3, _("Grand Total"), bold)
        sheet.write_number(row, 4, result.get("grand_total", 0), total_fmt)

        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 16)
        sheet.set_column(2, 2, 22)
        sheet.set_column(3, 3, 40)
        sheet.set_column(4, 4, 16)
        sheet.set_column(5, 5, 26)
        sheet.set_column(6, 6, 35)
        sheet.set_column(7, 7, 25)
        sheet.set_column(8, 8, 22)


class ReceiptReportPdf(models.AbstractModel):
    _name = "report.receipt_kmitl_summary_report.receipt_summary_pdf"
    _description = "Receipt Summary PDF"

    @api.model
    def _get_report_values(self, docids, data=None):
        options = (data or {}).get("options") or {}
        report = self.env["receipt_kmitl.receipt.report"]
        result = report.get_report_data(options)
        company = self.env["res.company"].browse(
            options.get("company_id") or self.env.company.id
        )
        return {
            "doc_ids": docids,
            "doc_model": "receipt_kmitl.report.wizard",
            "docs": self.env["receipt_kmitl.report.wizard"].browse(docids),
            "company": company,
            "groups": result.get("groups", []),
            "grand_total": result.get("grand_total", 0),
            "filter_lines": report.get_filter_lines(options),
            "format_amount": report.format_amount,
        }
