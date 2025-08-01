# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestTwoSubmittedLine(models.Model):
    _name = 'purchase.request.two.submitted.line'
    _description = 'PurchaseRequestTwoSubmittedLine'

    name = fields.Char('Name')

    submitted_id = fields.Many2one('purchase.request.two.submitted', string='Submitted')
    pr2_form_id = fields.Many2one('purchase.request.two', string='PR2 Form', required=True,  domain="[('payment_type', '=', payment_type_ref)]")

    vendor = fields.Many2one(related='pr2_form_id.vendor', string='Vendor', store=True, readonly=True)
    payment_type = fields.Selection(related='pr2_form_id.payment_type', string='Payment Type', store=True, readonly=True)

    payment_type_ref = fields.Selection(
        related='submitted_id.payment_type_ref',
        store=True,
        readonly=True
    )
