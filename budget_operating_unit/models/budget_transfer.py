# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetTransfer(models.Model):
    _inherit = 'budget.transfer'

    @api.model
    def _default_operating_unit_id(self):
        if (
            self._context.get("default_move_type", False)
            and self._context.get("default_move_type") != "entry"
        ):
            return self.env["res.users"].operating_unit_default_get()
        return False

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        default=_default_operating_unit_id,
        help="This operating unit will be defaulted in the move lines.",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
