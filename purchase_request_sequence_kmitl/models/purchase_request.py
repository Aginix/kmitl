# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            if vals.get("operating_unit_id"):
                ou = self.env["operating.unit"].browse(vals["operating_unit_id"])
                if ou.department_id:
                    vals["department_id"] = ou.department_id.id

            fy_id = self.env["account.fiscal.year"].browse(vals.get("account_fiscal_year_id"))
            fiscal_year = fy_id.name[-2:] if fy_id else fields.Date.today().strftime("%y")

            department = self.env["hr.department"].browse(vals.get("department_id"))
            short_name = department.short_name or "XXX"

            seq_code = f"purchase.request.{fiscal_year}.{short_name}"

            if not self.env['ir.sequence'].search([('code', '=', seq_code)], limit=1):
                self.env['ir.sequence'].create({
                    'name': f'Purchase Request {fiscal_year} {short_name}',
                    'code': seq_code,
                    'prefix': f'PR/{fiscal_year}/{short_name}/',
                    'padding': 4,
                    'number_increment': 1,
                })

            vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or _('New')

        records = super().create(vals_list)

        for rec in records:
            if rec.operating_unit_id and rec.operating_unit_id.department_id:
                rec.department_id = rec.operating_unit_id.department_id.id

        return records
