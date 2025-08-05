# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestSubmitLine(models.Model):
    _name = 'purchase.request.submit.line'
    _description = 'PurchaseRequestSubmitLine'

    name = fields.Char('Name')
    submitted_id = fields.Many2one('purchase.request.submit', string='Submitted')
    pr2_form_id = fields.Many2one('purchase.request.form', string='PR2 Form', required=True,  domain="[('payment_type', '=', payment_type_ref)]")
    vendor = fields.Many2one(related='pr2_form_id.vendor', string='Vendor', store=True, readonly=True)
    payment_type = fields.Selection(related='pr2_form_id.payment_type', string='Payment Type', store=True, readonly=True)

    payment_type_ref = fields.Selection(
        related='submitted_id.payment_type',
        store=True,
        readonly=True
    )
    ref = fields.Char(
        string='Reference',
        related='pr2_form_id.ref',
        store=True,
        readonly=True
    )

