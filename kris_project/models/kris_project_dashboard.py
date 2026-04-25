import logging
from collections import defaultdict
from datetime import date

from odoo import _, api, models

_logger = logging.getLogger(__name__)


class KrisProjectDashboard(models.Model):
    _inherit = "kris.project"

    @api.model
    def get_dashboard_data(self, filters=None):
        """Return aggregated data for the KRIS Project Dashboard."""
        if filters is None:
            filters = {}

        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        category_id = filters.get("category_id")
        type_id = filters.get("type_id")
        fiscal_year_id = filters.get("fiscal_year_id")

        # --- Projects ---
        project_domain = []
        if category_id:
            project_domain.append(("project_category_id", "=", int(category_id)))
        if type_id:
            project_domain.append(("project_type_id", "=", int(type_id)))
        if fiscal_year_id:
            project_domain.append(
                ("account_fiscal_year_id", "=", int(fiscal_year_id))
            )

        projects = self.search(project_domain)
        project_ids = projects.ids

        # --- Receipts (date-filtered) ---
        receipt_domain = [("project_id", "in", project_ids)]
        if date_from:
            receipt_domain.append(("date", ">=", date_from))
        if date_to:
            receipt_domain.append(("date", "<=", date_to))
        receipts = self.env["kris.project.receipt"].search(receipt_domain)

        # --- Cards ---
        total_estimated = sum(projects.mapped("project_value"))
        total_received = sum(receipts.mapped("amount"))

        alloc_lines = self.env["kris.project.allocation.line"].search(
            [("project_id", "in", project_ids)]
        )
        kris_lines = alloc_lines.filtered(lambda l: l.name == "KRIS")
        kris_actual = sum(kris_lines.mapped("actual_amount"))
        kris_estimated = sum(kris_lines.mapped("estimated_amount"))
        achievement_pct = (
            (total_received / total_estimated * 100) if total_estimated else 0.0
        )

        # --- by_type: KRIS allocation grouped by project sub-type ---
        by_type = {}
        for project in projects:
            type_name = (
                project.project_type_id.name
                if project.project_type_id
                else _("(ไม่มีประเภท)")
            )
            if type_name not in by_type:
                by_type[type_name] = {"kris_estimated": 0.0, "kris_actual": 0.0}
            for line in project.allocation_line_ids.filtered(
                lambda l: l.name == "KRIS"
            ):
                by_type[type_name]["kris_estimated"] += line.estimated_amount
                by_type[type_name]["kris_actual"] += line.actual_amount

        by_type_list = sorted(
            [
                {
                    "label": k,
                    "kris_estimated": v["kris_estimated"],
                    "kris_actual": v["kris_actual"],
                }
                for k, v in by_type.items()
            ],
            key=lambda x: x["kris_actual"],
            reverse=True,
        )

        # --- combo: monthly receipts for current & previous calendar year ---
        current_year = date.today().year
        prev_year = current_year - 1
        monthly_current = defaultdict(float)
        monthly_prev = defaultdict(float)
        for receipt in receipts:
            if receipt.date:
                y = receipt.date.year
                m = receipt.date.month
                if y == current_year:
                    monthly_current[m] += receipt.amount
                elif y == prev_year:
                    monthly_prev[m] += receipt.amount

        combo_data = {
            "current_year": current_year,
            "prev_year": prev_year,
            "current": [monthly_current.get(m, 0.0) for m in range(1, 13)],
            "prev": [monthly_prev.get(m, 0.0) for m in range(1, 13)],
        }

        # --- top_leaders: top 10 by total received amount ---
        leader_amounts = defaultdict(float)
        for receipt in receipts:
            if receipt.project_id.leader_id:
                leader_amounts[receipt.project_id.leader_id.name] += receipt.amount
        top_leaders_list = [
            {"name": n, "amount": a}
            for n, a in sorted(
                leader_amounts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # --- heatmap: faculty × allocation type (actual amounts) ---
        heatmap_data = defaultdict(
            lambda: {"central": 0.0, "faculty_dept": 0.0, "kris": 0.0}
        )
        for project in projects:
            department_name = (
                project.department_id.complete_name
                if project.department_id
                else _("(ไม่ระบุ)")
            )
            for line in project.allocation_line_ids:
                if line.name == "ส่วนกลาง":
                    heatmap_data[department_name]["central"] += line.actual_amount
                elif line.name in ("คณะ/ส่วนงาน", "ภาค/หน่วยงาน"):
                    heatmap_data[department_name]["faculty_dept"] += line.actual_amount
                elif line.name == "KRIS":
                    heatmap_data[department_name]["kris"] += line.actual_amount

        heatmap_rows = [
            {
                "name": name,
                "central": data["central"],
                "faculty_dept": data["faculty_dept"],
                "kris": data["kris"],
            }
            for name, data in sorted(heatmap_data.items())
        ]

        # --- filter_options ---
        categories = self.env["kris.project.category"].search([])
        types = self.env["kris.project.type"].search([])
        fiscal_years = self.env["account.fiscal.year"].search(
            [], order="date_from desc"
        )

        return {
            "cards": {
                "total_estimated": total_estimated,
                "total_received": total_received,
                "kris_actual": kris_actual,
                "kris_estimated": kris_estimated,
                "achievement_pct": achievement_pct,
            },
            "by_type": by_type_list,
            "combo": combo_data,
            "top_leaders": top_leaders_list,
            "heatmap": heatmap_rows,
            "filter_options": {
                "categories": [{"id": c.id, "name": c.name} for c in categories],
                "types": [
                    {"id": t.id, "name": t.name, "category_id": t.category_id.id}
                    for t in types
                ],
                "fiscal_years": [
                    {"id": fy.id, "name": fy.name} for fy in fiscal_years
                ],
            },
        }
