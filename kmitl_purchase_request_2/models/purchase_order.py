# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    request_ids = fields.Many2many(
        comodel_name='purchase.request',
        relation='purchase_request_po_rel',
        column1='purchase_order_id',
        column2='request_id',
        string='Purchase Requests',
    )

    state = fields.Selection([
        ('draft', 'PR2'),
        ('sent', 'PR2 Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        help="The department associated with this purchase order."
    )
    request_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
    )
    approval_date = fields.Date(
        string='อนุมัติวันที่',
        help="The date when the purchase order was approved. If not set, it will be the current date."
    )
    approval_by = fields.Many2one(
        'res.users',
        string='อนุมัติโดย',
        help="The user who approved the purchase order. If not set, it will be the current user."
    )
    payment_type = fields.Selection(
        [('prepaid', 'Prepaid'), ('postpaid', 'Postpaid')],
        string='ประเภทการชำระเงิน',
        help="Select the payment type for this purchase order. Prepaid means payment is made before delivery, Postpaid means payment is made after delivery."
    )

