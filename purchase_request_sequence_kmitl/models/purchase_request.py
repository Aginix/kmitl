# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            fy_id = self.env["account.fiscal.year"].browse(vals.get("account_fiscal_year_id"))
            fiscal_year = fy_id.name[-2:] if fy_id else fields.Date.today().strftime("%y")

            department = self.env["hr.department"].browse(vals.get("department_id"))
            short_name = department.short_name or ""

            seq_code = f"purchase.request.{fiscal_year}.{short_name}"

            Sequence = self.env['ir.sequence'].sudo()

            if not Sequence.search([('code', '=', seq_code)], limit=1):
                Sequence.create({
                    'name': f'Purchase Request {fiscal_year} {short_name}',
                    'code': seq_code,
                    'prefix': f'PR/{fiscal_year}/{short_name}/',
                    'padding': 4,
                    'number_increment': 1,
                })

            vals['name'] = Sequence.next_by_code(seq_code) or _('New')

        return super().create(vals_list)
