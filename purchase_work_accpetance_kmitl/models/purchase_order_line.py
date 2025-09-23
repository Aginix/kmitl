# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_restrict_qty_accepted(self):
       for line in self:
           if line.qty_accepted > 0:
               raise UserError(
                   _(
                       "You cannot delete a purchase order line with accepted quantity. "
                   )
               )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase_or_done(self):
        return
