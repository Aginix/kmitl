# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    total_estimated_cost = fields.Monetary(
        string="Total Estimated Cost from Requests",
        compute="_compute_total_estimated_cost",
        store=True,
        currency_field="currency_id",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        help="The department associated with this purchase order.",
        readonly=True,
    )
    request_by = fields.Many2one(
        "res.users",
        string="Requested By",
        default=lambda self: self.env.user,
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
    contract_type = fields.Selection(
        related='approval_id.contract_type',
        string="Contract type",
        store=True,
        readonly=True
    )
    work_start_date = fields.Date(
        string="Work start date",
        help="The start date for the purchase order. If not set, the current date will be used.",
    )
    work_end_date = fields.Date(
        string="Work end date",
        help="The end date for the purchase order. If not set, the start date will be used.",
    )
    purchase_request_name = fields.Char(
        string="Purchase request name",
        help="The name of the purchase request associated with the selected lines.",
    )
    fee = fields.Char(
        string="Fee per day"
    )
    request_id = fields.Many2one('purchase.request', string="PR1", readonly=True)
    approval_id = fields.Many2one('purchase.request.approval', string="PR2", readonly=True)
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
    bid_line_ids = fields.One2many('purchase.order.bidder.line', 'order_id', string='Bidder line')
    document_ids = fields.One2many(
        "purchase.order.attachment",
        "request_id",
        string="Attachment",
    )
    request_total = fields.Monetary(related='approval_id.estimated_cost', string="PR1 Total")

    @api.depends("request_id.line_ids.estimated_cost")
    def _compute_total_estimated_cost(self):
        for record in self.request_id:
            self.total_estimated_cost = sum(record.line_ids.mapped("estimated_cost"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.custom') or _('New')
        return super().create(vals_list)
