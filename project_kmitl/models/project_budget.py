# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectBudget(models.Model):
    _name = "project.budget"
    _description = "Project Budget"

    name = fields.Char("Name", required=True)
    # expression_ids = fields.One2many(
    #     string="Expressions",
    #     comodel_name="project.budget.expression",
    #     inverse_name="project_id",
    #     copy=True,
    # )
    description = fields.Char(compute="_compute_description")
    price_per_unit = fields.Float(required=True)
    unit_name = fields.Char(required=True)
    unit_multipier = fields.Char()

    @api.depends("name", "price_per_unit", "unit_name", "unit_multipier")
    def _compute_description(self):
        for record in self:
            record.description = ""

    # def _get_description(self, amount, multipier):
    #     return f"{amount} {self.unit_name} x {self.price_per_unit} บาท"


# class ProjectBudgetExpr(models.Model):
#     _name = "project.budget.expression"
#     _description = "Project Budget Expression"

