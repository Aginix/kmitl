# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Agreement(models.Model):
    _inherit = 'agreement'

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    project_ids = fields.Selection(
        [("project_1", "Project 1"), ("project_2", "Project 2")],
        string="Project",
    )

    document_ids = fields.One2many(
        "purchase.agreement.attachment",
        "request_id",
        string="Attachment",
    )

    purchase_order_id = fields.Many2one(
        'purchase.order', 
        string="PO Ref", 
        ondelete="set null",
    )

    pr1_total = fields.Monetary(related='purchase_order_id.pr1_total', string='PR1 Total')

    invoice_plan_ids = fields.One2many(
        comodel_name="purchase.invoice.plan",
        inverse_name="purchase_id",
        string="Invoice Plan",
        related="purchase_order_id.invoice_plan_ids",
        readonly=True,
    )

    work_acceptance_committee_ids = fields.One2many(
        related='purchase_order_id.work_acceptance_committee_ids',
        readonly=True,
    )
    tor_committee_ids = fields.One2many(
        related='purchase_order_id.tor_committee_ids',
        readonly=True,
    )
    price_determine_committee_ids = fields.One2many(
        related='purchase_order_id.price_determine_committee_ids',
        readonly=True,
    )
    evaluation_committee_ids = fields.One2many(
        related='purchase_order_id.evaluation_committee_ids',
        readonly=True,
    )

    fee = fields.Char(
        related='purchase_order_id.fee',
        string='Fee Per Day',
    )