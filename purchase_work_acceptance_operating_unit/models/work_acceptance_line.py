# -*- coding: utf-8 -*-
from odoo import fields, models


class WorkAcceptanceLine(models.Model):
    _inherit = "work.acceptance.line"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="wa_id.operating_unit_id",
        string="Operating Unit",
        store=True,
    )
