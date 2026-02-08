# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _create_disbursement_request(self):
        disbursement_request = super()._create_disbursement_request()
        disbursement_request.action_submit()
        return disbursement_request
