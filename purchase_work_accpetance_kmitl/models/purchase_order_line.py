# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_restrict_qty_accepted(self):
        restricted = self.filtered(lambda l: l.qty_accepted > 1)
        if restricted:
            raise UserError(_(
                "You cannot delete order lines that have accepted quantity greater than 1.\n"
                "Affected lines: %s"
            ) % ", ".join(restricted.mapped("name")))
