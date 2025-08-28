from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    approval_id = fields.Many2one(
        "purchase.request.approval",
        string="PR2",
    )

    def action_create_approval(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.approval.wizard',
            'view_mode': 'form',
            'target': 'new',
            'name': "กรุณาบันทึกข้อมูลเพื่อจัดทำคำขออนุมัติ",
            'context': {'active_id': self.id}
        }
