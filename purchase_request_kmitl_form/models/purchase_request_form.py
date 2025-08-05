# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestForm(models.Model):
    _name = 'purchase.request.form'
    _description = 'PurchaseRequestForm'
    _rec_name = 'ref'

    _STATES = [
        ("draft", "Draft"),
        ("submit", "Submit"),
        ("approve", "approved"),
        ("reject", "reject"),
    ]

    ref = fields.Char(string="reference")
    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )
    vendor = fields.Many2one(
        "res.partner",
        string="Vendor",
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]},
        help="Select a vendor to create a purchase order for the selected request lines.",
    )
    start_date = fields.Date(
        string="วันที่เริ่มสัญญา",
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]},
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    end_date = fields.Date(
        string="วันที่สิ้นสุดสัญญา",
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]},
        help="The end date for the purchase order. If not set, the start date will be used.",
    )
    purchase_type = fields.Selection(
        [("standard", "Standard"), ("urgent", "Urgent")],
        string="ประเภทสัญญา",
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]},
        help="Select the type of purchase order to create. Standard for regular orders, Urgent for expedited orders.",
    )
    purchase_request_name = fields.Char(
        string="ชื่อใบสั่งซื้อ/จ้าง",
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]},
        help="The name of the purchase request associated with the selected lines.",
    )
    payment_type = fields.Selection([
        ("direct", "จ่ายตรง"),
        ("loan", "เงินยืม"),
        ("prepaid", "สำรองจ่าย")
    ], string="ประเภทการจ่ายเงิน",states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]})
    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]},
        string="PR1",
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    submit_id = fields.Many2one(
        'purchase.request.submit',
        string='submit id',
        ondelete='cascade',
    )
    approve_by = fields.Many2one(
        'res.users',
        string='Approved By',
        states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]}
    )
    approve_date = fields.Datetime(
        string='Approved Date',
    )
    amount_untaxed = fields.Monetary(string='รวมเป็นเงิน', compute='_compute_amount', currency_field='currency_id')
    amount_tax = fields.Monetary(string='ภาษีมูลค่าเพื่ม', compute='_compute_amount',currency_field='currency_id')
    amount_total = fields.Monetary(string='รวมเป็นเงินทั้งสิ้น', compute='_compute_amount',currency_field='currency_id')
    purchas_request_line_ids = fields.One2many(related='purchase_request_id.line_ids')
    line_ids = fields.One2many('purchase.request.form.line', 'pr2_id', string='Products', states={"submit": [("readonly", True)],
        "approve": [("readonly", True)]})

    def button_submit(self):
        return self.write({"state": "submit"})

    def button_approve(self):
        return self.write({"state": "approve" , "approve_by":self.env.user.id , "approve_date":datetime.now() })

    def button_reject(self):
        return self.write({"state": "reject"})

    def button_reset(self):
        return self.write({"state": "draft"})

    def button_create(self):
        self.ensure_one()

        submit_record = self.env['purchase.request.submit'].create({
            'payment_type': self.payment_type,
            'request_by': self.env.user.id,
            'line_ids': [(0, 0, {
                'pr2_form_id': self.id,
            })]
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Request Submit',
            'res_model': 'purchase.request.submit',
            'view_mode': 'form',
            'res_id': submit_record.id,
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('ref'):
                vals['ref'] = self.env['ir.sequence'].next_by_code('purchase.request.form')
        return super().create(vals_list)

    @api.depends('line_ids.quantity', 'line_ids.unit_price', 'line_ids.taxes')
    def _compute_amount(self):
        for rec in self:
            untaxed = 0.0
            taxes = 0.0
            currency = rec.currency_id
            for line in rec.line_ids:
                subtotal = line.quantity * line.unit_price
                tax_amount = sum(
                    tax._compute_amount(subtotal, 1, product=line.product_id, partner=rec.vendor)
                    for tax in line.taxes
                )
                untaxed += subtotal
                taxes += tax_amount
            rec.amount_untaxed = untaxed
            rec.amount_tax = taxes
            rec.amount_total = untaxed + taxes
