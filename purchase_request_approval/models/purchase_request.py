from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    approval_ids = fields.One2many(
        'purchase.request.approval',
        'request_id',
        string='Approval'
    )

    def action_create_approval(self):
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
                'quantity': line.product_qty,
                'unit_price' : line.estimated_cost/line.product_qty,
            }))
        approval.write({'line_ids': line_vals})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.approval',
            'view_mode': 'form',
            'res_id': approval.id,
            'target': 'current',
        }
