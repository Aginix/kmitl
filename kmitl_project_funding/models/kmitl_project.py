from odoo import api, fields, models


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    funding_in_progress = fields.Float(
        string="อยู่ระหว่างดำเนินการ",
        digits="Product Price",
        compute="_compute_funding",
        compute_sudo=True,
        help="ยอดโอนเข้าโครงการที่ยังไม่ผ่าน (รอส่งขออนุมัติ / กำลังเวียนสารบรรณ / ตีกลับเพื่อแก้ไข)",
    )
    funding_shortfall = fields.Float(
        string="ยังขาด",
        digits="Product Price",
        compute="_compute_funding",
        compute_sudo=True,
        help="งบประมาณโครงการ − งบประมาณที่ได้รับการจัดสรร − อยู่ระหว่างดำเนินการ",
    )

    @api.depends("budget_estimate", "budget_amount")
    def _compute_funding(self):
        groups = self.env["kmitl.project.funding"].read_group(
            [("project_id", "in", self._origin.ids), ("status", "=", "in_progress")],
            ["amount:sum"],
            ["project_id"],
        )
        in_progress = {g["project_id"][0]: g["amount"] for g in groups}
        for rec in self:
            rec.funding_in_progress = in_progress.get(rec._origin.id, 0.0)
            rec.funding_shortfall = max(
                rec.budget_estimate - rec.budget_amount - rec.funding_in_progress,
                0.0,
            )

    def action_open_funding(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "kmitl_project_funding.action_kmitl_project_funding"
        )
        action["domain"] = [("project_id", "=", self.id)]
        return action
