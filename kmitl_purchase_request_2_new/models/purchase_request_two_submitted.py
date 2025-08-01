# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestTwoSubmitted(models.Model):
    _name = 'purchase.request.two.submitted'
    _description = 'PurchaseRequestTwoSubmitted'

    name = fields.Char(string='Submitted Ref', required=True, default=lambda self: _('New'))
    generate_po = fields.Boolean(string='Generate Purchase Order?', default=False)
    pr2_id = fields.Many2one('purchase.request.two', string='Related PR2 Form')

    purchase_order_id = fields.Many2one('purchase.order', string='Linked Purchase Order', readonly=True)

    line_ids = fields.One2many('purchase.request.two.submitted.line', 'submitted_id', string="PR2 Forms")

    payment_type_ref = fields.Selection(
        [("direct", "จ่ายตรง"),("loan", "เงินยืม"),("prepaid", "สำรองจ่าย")],
        string="Reference Payment Type",
        compute="_compute_payment_type_ref",
        store=True,
    )

    @api.depends('line_ids.pr2_form_id.payment_type')
    def _compute_payment_type_ref(self):
        for rec in self:
            first_line = rec.line_ids.filtered(lambda l: l.pr2_form_id.payment_type)
            rec.payment_type_ref = first_line[0].pr2_form_id.payment_type if first_line else False

    def action_submit(self):
        for rec in self:
            if rec.generate_po:
                po_vals = {
                    'partner_id': rec.pr2_id.vendor.id,
                    'order_line': [],
                }
                for line in rec.pr2_id.line_ids:
                    po_vals['order_line'].append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.description,
                        'product_qty': line.quantity,
                        'price_unit': line.unit_price,
                        'taxes_id': [(6, 0, line.taxes.ids)],
                    }))
                po = self.env['purchase.order'].create(po_vals)
                rec.purchase_order_id = po.id
