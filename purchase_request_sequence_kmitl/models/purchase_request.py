# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.model
    def create(self, vals):
        if not vals.get("department_id") and vals.get("operating_unit_id"):
            ou = self.env["operating.unit"].browse(vals["operating_unit_id"])
            if ou.department_id:
                vals["department_id"] = ou.department_id.id

        if vals.get("name", "/") == "/":
            fy = self.env["account.fiscal.year"].browse(vals.get("date_range_fy_id"))
            year = fy.name[-2:] if fy else fields.Date.today().strftime("%y")

            dept = self.env["hr.department"].browse(vals.get("department_id"))
            short_name = dept.short_name or "XXX"

            prefix = f"PR1/{year}/{short_name}/"
            last = self.search([("name", "like", prefix + "%")], order="name desc", limit=1)

            if last:
                last_seq = int(last.name.split("/")[-1])
                new_seq = str(last_seq + 1).zfill(4)
            else:
                new_seq = "0001"

            vals["name"] = prefix + new_seq

        return super().create(vals)

