# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequestReport(models.Model):
    _inherit = 'purchase.request.report'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: (self.env["res.users"].operating_unit_default_get()),
        readonly=False,
        recursive=True,
        store=True
    )
