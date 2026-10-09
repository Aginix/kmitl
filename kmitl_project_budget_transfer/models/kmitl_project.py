from odoo import api, fields, models


class KmitlProject(models.Model):
    """A project another unit may fund (ADR-0008).

    A project's ``kmitl_project`` analytic is minted scoped to the project's
    operating unit, so other units cannot pick it on a budget transfer. Ticking
    the flag clears that scope — the analytic becomes visible system-wide — so a
    supporting unit can transfer budget INTO the project's own coordinate.
    Unticking restores the owning unit's scope.
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
