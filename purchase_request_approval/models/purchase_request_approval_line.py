from odoo import _, api, fields, models


class PurchaseRequestApprovalLine(models.Model):
    _name = 'purchase.request.approval.line'
    _description = 'Purchase Request Approval Line'

    approval_id = fields.Many2one('purchase.request.approval', string='PR2')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    uom = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)
    company_id = fields.Many2one('res.company', string='Company', related='approval_id.company_id', readonly=True)
    product_qty = fields.Float(string='Quantity')
    description = fields.Text(string='Description')
    price_unit = fields.Float(string='Unit Price')
    taxes_id = fields.Many2many('account.tax', string='Taxes')
    currency_id = fields.Many2one(related='approval_id.currency_id', store=True, readonly=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.approval_id.vendor,
            currency=self.approval_id.currency_id,
            product=self.product_id,
            taxes=self.taxes_id,
            price_unit=self.price_unit,
            quantity=self.product_qty,
            price_subtotal=self.price_subtotal,
        )
