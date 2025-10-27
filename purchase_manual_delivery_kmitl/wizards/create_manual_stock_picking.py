# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateManualStockPicking(models.TransientModel):
    _inherit = 'create.stock.picking.wizard'

    picking_type_id = fields.Many2one(
        related='purchase_id.picking_type_id',
        string="Operation Type",
        readonly=True
        )

class CreateManualStockPickingWizardLine(models.TransientModel):
    _inherit = 'create.stock.picking.wizard.line'

    price_unit = fields.Float(
        readonly=False
    )