from odoo import _, api, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _name = 'purchase.request.approval.line'
    _description = 'Purchase Request Approval Line'

    approval_id = fields.Many2one('purchase.request.approval', string='PR2')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    uom = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    company_id = fields.Many2one('res.company', string='Company', related='approval_id.company_id', readonly=True)
    quantity = fields.Float(string='Quantity')
    description = fields.Text(string='Description')
    unit_price = fields.Float(string='Unit Price')
    taxes = fields.Many2many('account.tax', string='Taxes')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one(related='approval_id.currency_id', store=True, readonly=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price
