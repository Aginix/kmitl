# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models

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
            ("state", "in", ["confirmed", "posted"]),
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
                "dimensions": ", ".join(dim_parts),
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
