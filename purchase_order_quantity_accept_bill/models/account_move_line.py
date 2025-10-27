# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('display_type')
    def _compute_quantity(self):
        for line in self:
            if line.display_type == 'product':
                line.quantity = line.qty_accepted
            else:
                line.quantity = False
