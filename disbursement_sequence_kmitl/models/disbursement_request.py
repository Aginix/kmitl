# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    @api.model_create_multi
    def create(self, vals_list):
        """Assign DR/<fy>/<padding> as the request name, creating a new
        ir.sequence per fiscal year on first use.
        """
        Sequence = self.env["ir.sequence"].sudo()
        Company = self.env["res.company"]
        for vals in vals_list:
            if vals.get("name") and vals["name"] != "/":
                continue

            date = fields.Date.to_date(
                vals.get("date") or fields.Date.context_today(self)
            )
            company = Company.browse(
                vals.get("company_id") or self.env.company.id
            )
            fy = company.find_daterange_fy(date) if company else False
            fy_year = fy.name[-2:] if fy else date.strftime("%y")

            seq_code = f"disbursement.request.{fy_year}"
            if not Sequence.search([("code", "=", seq_code)], limit=1):
                Sequence.create({
                    "name": f"Disbursement Request {fy_year}",
                    "code": seq_code,
                    "prefix": f"DR/{fy_year}/",
                    "padding": 4,
                    "number_increment": 1,
                })

            vals["name"] = Sequence.next_by_code(seq_code) or _("New")

        return super().create(vals_list)
