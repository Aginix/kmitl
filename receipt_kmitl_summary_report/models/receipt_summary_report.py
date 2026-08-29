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


class ReceiptReport(models.AbstractModel):
    _name = "receipt_kmitl.receipt.report"
    _description = "Receipt Report Data Provider"

    @api.model
    def get_report_data(self, options):
        options = options or {}
        company_id = options.get("company_id") or self.env.company.id
        date_from = options.get("date_from")
        date_to = options.get("date_to")
        if not date_from or not date_to:
            return {"rows": [], "groups": []}

        domain = [
            ("company_id", "=", company_id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("state", "in", ["to_submit", "submitted", "approved", "done"]),
        ]

        payment_type = options.get("payment_type")
        if payment_type:
            domain.append(("payment_method_id.payment_type", "=", payment_type))

        dims = options.get("dims") or {}
        for field_name, code in DIMENSION_FIELDS:
            ids = dims.get(code) or []
            if ids:
                Analytic = self.env["account.analytic.account"]
                ids = Analytic.search([("id", "child_of", ids)]).ids
                domain.append((field_name, "in", ids))

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

            description = r.department_analytic_id.display_name or ""
            if r.description:
                description += "\n" + r.description

            rows.append({
                "id": r.id,
                "date": str(r.date),
                "name": r.name or "/",
                "description": description,
                "amount_total": r.amount_total,
                "dimensions": "\n".join(dim_parts),
                "note": r.note or "",
                "state": r.state,
                "payment_method": (
                    r.payment_method_id.name if r.payment_method_id else ""
                ),
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

        sheet.merge_range(0, 0, 0, 5, company.display_name, bold)
        sheet.merge_range(1, 0, 1, 5, _("Receipt Summary Report"), bold)
        sheet.merge_range(
            2, 0, 2, 5,
            "%s %s %s %s" % (
                _("From"), options.get("date_from") or "",
                _("to"), options.get("date_to") or "",
            ),
        )

        headers = [
            _("Date"), _("Receipt No."), _("Description"),
            _("Amount"), _("Analytic Dimensions"), _("Note"),
        ]
        row = 4
        for col, label in enumerate(headers):
            sheet.write(row, col, label, head)

        row = 5
        for group in result.get("groups", []):
            sheet.write(row, 0, group["date"], group_fmt)
            sheet.write(row, 1, "", group_fmt)
            sheet.write(row, 2, "", group_fmt)
            sheet.write_number(row, 3, group["total"], group_num)
            sheet.write(row, 4, "", group_fmt)
            sheet.write(row, 5, "", group_fmt)
            row += 1
            for r in group["rows"]:
                sheet.write(row, 0, "", cell)
                sheet.write(row, 1, r["name"], cell)
                sheet.write(row, 2, r["description"], wrap)
                amt = r["amount_total"] or 0
                if abs(amt) >= 0.005:
                    sheet.write_number(row, 3, amt, num)
                else:
                    sheet.write_blank(row, 3, None, num)
                sheet.write(row, 4, r["dimensions"], wrap)
                sheet.write(row, 5, r["note"], cell)
                row += 1

        row += 1
        sheet.write(row, 2, _("Grand Total"), bold)
        sheet.write_number(row, 3, result.get("grand_total", 0), total_fmt)

        sheet.set_column(0, 0, 12)
        sheet.set_column(1, 1, 16)
        sheet.set_column(2, 2, 35)
        sheet.set_column(3, 3, 16)
        sheet.set_column(4, 4, 35)
        sheet.set_column(5, 5, 25)
