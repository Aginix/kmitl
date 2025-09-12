# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.onchange("operating_unit_id")
    def _onchange_operating_unit_id(self):
        domain = [("root_plan_id.code", "=", "departments")]
        if self.operating_unit_id:
            domain.append(("operating_unit_ids", "in", self.operating_unit_id.id))
        return {"domain": {"department_analytic_id": domain}}
