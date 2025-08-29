from odoo import _, api, fields, models, Command
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    approval_id = fields.Many2one(
        "purchase.request.approval",
        string="PR2",
    )

    def button_approved(self):
        self.ensure_one()
        res = super().button_approved()
        self._create_approval()
        return res

    def _prepare_approval_vals(self):
        return {
            'request_id': self.id,
            'purchase_request_number': self.name,
            'line_ids': [Command.create(line._prepare_approval_line_vals()) for line in self.line_ids],
        }

    def _create_approval(self):
        approval = self.env['purchase.request.approval'].create(self._prepare_approval_vals())
        self.write({'approval_id': approval.id})
