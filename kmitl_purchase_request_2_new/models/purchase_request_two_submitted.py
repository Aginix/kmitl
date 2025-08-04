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

    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        help="The department associated with this purchase order.",
    )
    request_by = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
    )

    approval_date = fields.Date(
        string="อนุมัติวันที่",
        help="The date when the purchase order was approved. If not set, it will be the current date.",
    )
    approval_by = fields.Many2one(
        "res.users",
        string="อนุมัติโดย",
        help="The user who approved the purchase order. If not set, it will be the current user.",
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    def button_draft(self):
        self.state = 'draft'

    def button_approved(self):
        self.state = 'approved'
    
    def button_rejected(self):
        self.state = 'rejected'

    @api.depends('line_ids.pr2_form_id.payment_type')
    def _compute_payment_type_ref(self):
        for rec in self:
            first_line = rec.line_ids.filtered(lambda l: l.pr2_form_id.payment_type)
            rec.payment_type_ref = first_line[0].pr2_form_id.payment_type if first_line else False

    def action_submit_po(self):
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
