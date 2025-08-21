from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    def action_create_pr_approval(self):
        self.ensure_one()

        pr2 = self.env['purchase.request.approval.form'].create({
            'pr1_ref': self.id,
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
        pr2.write({'line_ids': line_vals})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.approval.form',
            'view_mode': 'form',
            'res_id': pr2.id,
            'target': 'current',
        }
