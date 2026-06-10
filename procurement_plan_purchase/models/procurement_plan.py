from odoo import _, fields, models
from odoo.exceptions import UserError


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    procurement_method_id = fields.Many2one(
        comodel_name="procurement.method",
        string="Procurement Method",
        required=False,
        tracking=True,
    )

    def action_ready(self):
        for rec in self:
            if not rec.procurement_method_id:
                raise UserError(_("กรุณาระบุแผนการดำเนินงานให้เสร็จสิ้นทั้งหมด"))
        return super().action_ready()
