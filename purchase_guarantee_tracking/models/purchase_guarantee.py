# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    reference = fields.Reference(
        tracking=True,
    )
    reference_model = fields.Char(
        tracking=True,
    )
    requisition_id = fields.Many2one(
        tracking=True,
    )
    purchase_id = fields.Many2one(
        tracking=True,
    )
    guarantee_method_id = fields.Many2one(
        tracking=True,
    )
    partner_id = fields.Many2one(
        tracking=True,
    )
    guarantee_type_id = fields.Many2one(
        tracking=True,
    )
    company_id = fields.Many2one(
        tracking=True,
    )
    amount = fields.Monetary(
        tracking=True,
    )
    date_guarantee_receive = fields.Date(
        tracking=True,
    )
    analytic_account_id = fields.Many2one(
        tracking=True,
    )
    amount_received = fields.Monetary(
        tracking=True,
    )
    document_ref = fields.Char(
        tracking=True,
    )
    date_return = fields.Date(
        tracking=True,
    )
    amount_returned = fields.Monetary(
        tracking=True,
    )
    date_due_guarantee = fields.Date(
        tracking=True,
    )
    note = fields.Text(
        tracking=True,
    )
    active = fields.Boolean(
        tracking=True,
    )