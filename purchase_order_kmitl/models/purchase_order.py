# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    responsible_id = fields.Many2one(
        "res.users",
        string="Responsible Person",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    approval_date = fields.Date(
        string="Approve date",
        help="The date when the purchase order was approved. If not set, it will be the current date.",
    )
    approval_by = fields.Many2one(
        "res.users",
        string="Approve by",
        help="The user who approved the purchase order. If not set, it will be the current user.",
    )
    payment_type = fields.Selection(
        [("prepaid", "Prepaid"), ("postpaid", "Postpaid")],
        string="ประเภทการชำระเงิน",
        help="Select the payment type for this purchase order. Prepaid means payment is made before delivery, Postpaid means payment is made after delivery.",
    )
    contract_start_date = fields.Date(
        string="Contract start date",
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    contract_end_date = fields.Date(
        string="Contract End date",
        help="The end date for the purchase order. If not set, the start date will be used.",
    )
    work_start_date = fields.Date(
        string="Work start date",
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    work_end_date = fields.Date(
        string="Work end date",
        help="The end date for the purchase order. If not set, the start date will be used.",
    )
    fee = fields.Char(
        string="Fee per day"
    )

    bid_line_ids = fields.One2many('purchase.order.bidder.line', 'order_id', string='Bidder line')
    document_ids = fields.One2many(
        "purchase.order.attachment",
        "request_id",
        string="Attachment",
    )

    request_id = fields.Many2one('purchase.request', string="PR1", readonly=True)
    request_approval_id = fields.Many2one('purchase.request.approval', string="PR2", readonly=True)

    # Related fields
    description = fields.Char(
        related="request_approval_id.description",
        readonly=True,
        help="The name of the purchase request associated with the selected lines.",
    )
    contract_type = fields.Selection(
        related='request_approval_id.contract_type',
        string="Contract type",
        store=True,
        readonly=True
    )
    work_acceptance_committee_ids = fields.One2many(
        related='request_id.work_acceptance_committee_ids',
        readonly=True,
    )
    tor_committee_ids = fields.One2many(
        related='request_id.tor_committee_ids',
        readonly=True,
    )
    price_determine_committee_ids = fields.One2many(
        related='request_id.price_determine_committee_ids',
        readonly=True,
    )
    evaluation_committee_ids = fields.One2many(
        related='request_id.evaluation_committee_ids',
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.kmitl') or _('New')
        return super().create(vals_list)
