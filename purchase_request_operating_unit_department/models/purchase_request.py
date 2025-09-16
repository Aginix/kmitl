# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.onchange("operating_unit_id")
    def _onchange_operating_unit_id(self):
        for rec in self:
            if rec.operating_unit_id and rec.operating_unit_id.department_id:
                rec.department_id = rec.operating_unit_id.department_id
            else:
                rec.department_id = False
