# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetMoveLine(models.Model):
    _inherit = 'budget.move.line'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("move_id", False):
                move = self.env["budget.move"].browse(vals["move_id"])
                if move.operating_unit_id:
                    vals["operating_unit_id"] = move.operating_unit_id.id
        return super().create(vals_list)
