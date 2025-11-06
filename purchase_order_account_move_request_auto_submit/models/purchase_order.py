# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _prepare_move_request_vals(self):
        vals = super()._prepare_move_request_vals()
        vals.update({
            "state": "submitted",
        })
        return vals
