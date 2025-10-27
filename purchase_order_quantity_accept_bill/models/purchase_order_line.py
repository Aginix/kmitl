# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or self.date_order or self.order_id.date_order or fields.Date.today()

        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res['quantity'] = self.qty_accepted
        return res
