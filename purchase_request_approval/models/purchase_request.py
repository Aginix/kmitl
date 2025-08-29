from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    approval_id = fields.Many2one(
        "purchase.request.approval",
        string="PR2",
    )

    def button_approved(self):
        self.ensure_one()
        approval = self.env['purchase.request.approval'].create({
            'request_id': self.id,
            'purchase_request_number': self.name,
        })

        line_vals = []
        for line in self.line_ids:
            line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'description': line.name,
                'product_qty': line.product_qty,
                'price_unit': line.estimated_cost / line.product_qty if line.product_qty else 0,
            }))
        self.write({'approval_id': approval.id})
        approval.write({'line_ids': line_vals})

        return super().button_approved()
