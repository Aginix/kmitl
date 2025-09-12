# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseGuarantee(models.Model):
    _inherit = 'purchase.guarantee'

    is_purchase_order = fields.Boolean(
        string="Is Purchase Order",
        compute="_compute_reference",
        store=False,
        help="True if reference is purchase.order"
    )

    @api.depends("reference")
    def _compute_reference(self):
        res = super()._compute_reference()
        for rec in self:
            rec.request_id = False
            rec.is_purchase_request = False

            if rec.reference:
                if rec.reference._name == "purchase.request":
                    rec.request_id = rec.reference
                    rec.reference_model = rec.reference._name
                    rec.is_purchase_request = True
                rec._check_reference_status()
        return res