import logging

from odoo import tools
from odoo import Command, api, fields, models

_logger = logging.getLogger(__name__)


class MisReportF5(models.AbstractModel):
    _name = _description = "mis.report.kmitl.f5"

    def _generate_report(self, appropriation_id):
        roots = self.env["account.analytic.account"].search(
            ["&", ("root_plan_id.code", "=", "activities"), ("parent_id", "=", False)],
            order="line_seq",
        )

        funds = self.env["account.analytic.account"].search(
            ["&", ("root_plan_id.code", "=", "funds"), ("parent_id", "=", False)],
            order="line_seq",
        )

        appropriation = self.env["budget.appropriation"].browse(appropriation_id)
        rows = []

        for root in roots:  # ด้าน
            rows.append({
                "name": "",
                "description": root.name,
                "code": root.code,
                "domain": [("activity_analytic_id.parent_path", "=like", root.parent_path + "%%")],
                "indent_level": 1,
            })
            lines = appropriation.line_ids.search([("activity_analytic_id.parent_path", "=like", root.parent_path + "%%")])
            for level1 in root.child_ids:  # แผนงาน
                rows.append({
                    "name": "",
                    "description": level1.name,
                    "code": level1.code,
                    "domain": [("activity_analytic_id.parent_path", "=like", level1.parent_path + "%%")],
                    "indent_level": 2,
                })
                for level2 in level1.child_ids:  # งาน
                    rows.append({
                        "name": "",
                        "description": level2.name,
                        "code": level2.code,
                        "domain": [("activity_analytic_id.parent_path", "=like", level2.parent_path + "%%")],
                        "indent_level": 3,
                    })
                    for level3 in level2.child_ids:  # กิจกรรม
                        for level4 in level3.child_ids:  # กิจกรรม
                            lines = appropriation.line_ids.search([("parent_path", "=", "")])
        return rows
