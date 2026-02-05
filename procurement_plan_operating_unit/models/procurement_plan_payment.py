# -*- coding: utf-8 -*-
from odoo import fields, models


class ProcurementPlanPayment(models.Model):
    _inherit = "procurement.plan.payment"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="procurement_plan_id.operating_unit_id",
        string="Operating Unit",
    )
