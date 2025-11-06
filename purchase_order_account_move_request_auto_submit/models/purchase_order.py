# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _create_move_request(self):
        move_request = super()._create_move_request()
        move_request.action_submit()
        return move_request
