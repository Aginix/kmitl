from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestApprovalWizard(models.TransientModel):
    _name = 'purchase.request.approval.wizard'
    _description = 'Wizard for Creating Purchase Request Approval'

    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        help="Select a vendor to create a purchase Request for the selected request lines.",
        domain="[('supplier_rank', '>', 0)]",
        required=True
    )
    purchase_request_name = fields.Char(
        string="Purchase Request Name",
        required=True
    )
    start_date = fields.Date(
        string="Start Date"
    )
    end_date = fields.Date(
        string="End Date"
    )

    def action_confirm(self):
        """สร้าง Approval จาก wizard"""
        self.ensure_one()
        active_request = self.env['purchase.request'].browse(self.env.context.get('active_id'))
        if not active_request:
            raise UserError(_("No active Purchase Request found."))

        approval = self.env['purchase.request.approval'].create({
            'request_id': active_request.id,
            'purchase_request_number': active_request.name,
            'purchase_request_name': self.purchase_request_name,
            'vendor': self.vendor_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
        })

        line_vals = []
        for line in active_request.line_ids:
            line_vals.append((0, 0, {
                'product_id': line.product_id.id,
                'description': line.name,
                'quantity': line.product_qty,
                'unit_price': line.estimated_cost / line.product_qty if line.product_qty else 0,
            }))
        active_request.write({'approval_id': approval.id})
        approval.write({'line_ids': line_vals})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request.approval',
            'view_mode': 'form',
            'res_id': approval.id,
            'target': 'current',
        }
