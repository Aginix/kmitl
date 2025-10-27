# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateManualStockPicking(models.TransientModel):
    _inherit = 'create.stock.picking.wizard'

    # maybe use from stock.picking.type ???
    operation_type = fields.Selection(
        [("receive", "Receive Product")],
        string="Operation Type",
        default="receive",
        readonly=True
        )

class CreateManualStockPickingWizardLine(models.TransientModel):
    _inherit = 'create.stock.picking.wizard.line'

    price_unit = fields.Float(
        readonly=False
    )