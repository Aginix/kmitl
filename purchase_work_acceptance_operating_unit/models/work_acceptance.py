# -*- coding: utf-8 -*-
from odoo import fields, models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(
            self.env.uid
        ),
    )
