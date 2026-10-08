from odoo import api, fields, models


class KmitlProject(models.Model):
    """A project another unit may fund (ADR-0008).

    A project's ``kmitl_project`` analytic is minted scoped to the project's
    operating unit, so other units cannot pick it on a budget transfer. Ticking
    the flag clears that scope — the analytic becomes visible system-wide — so a
    supporting unit can transfer budget INTO the project's own coordinate.
    Unticking restores the owning unit's scope.

    Also totals the project's Funding Summary (ADR-0007) beside the Estimate.
    """

    _inherit = "kmitl.project"

    is_supported_by_other_units = fields.Boolean(
        string="มีการสนับสนุนจากหน่วยงานอื่น",
        tracking=True,
        copy=False,
        help="ติ๊กเมื่อโครงการนี้ได้รับการสนับสนุนงบประมาณจากหน่วยงานอื่น — "
        "มิติโครงการ (analytic account) จะเปิดให้ทุกหน่วยงานมองเห็น "
        "เพื่อให้หน่วยงานผู้สนับสนุนเลือกโครงการนี้เป็นปลายทางในใบโอนงบประมาณได้ "
        "เอาติ๊กออกเพื่อจำกัดให้เห็นเฉพาะหน่วยงานเจ้าของโครงการตามเดิม",
    )

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

    @api.model
    def _create_analytic_account_from_values(self, values):
        analytic = super()._create_analytic_account_from_values(values)
        if self.is_supported_by_other_units:
            analytic.sudo().operating_unit_ids = [(5, 0, 0)]
        return analytic

    def write(self, vals):
        res = super().write(vals)
        if {"is_supported_by_other_units", "operating_unit_id"} & set(vals):
            self._sync_analytic_operating_units()
        return res

    def _sync_analytic_operating_units(self):
        """Open a supported project's analytic to every unit, else scope it to
        the project's own operating unit."""
        for project in self.filtered("analytic_account_id"):
            if project.is_supported_by_other_units:
                command = [(5, 0, 0)]
            else:
                command = [(6, 0, project.operating_unit_id.ids)]
            project.analytic_account_id.sudo().operating_unit_ids = command

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
            "kmitl_project_budget_transfer.action_kmitl_project_funding"
        )
        action["domain"] = [("project_id", "=", self.id)]
        return action
