# -*- coding: utf-8 -*-
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class BudgetCommitmentLine(models.Model):
    _inherit = 'budget.commitment.line'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="commitment_id.operating_unit_id",
        string="Operating Unit",
    )
