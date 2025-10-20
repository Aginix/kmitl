# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            fy_id = self.env["account.fiscal.year"].browse(vals.get("account_fiscal_year_id"))
            fiscal_year = fy_id.name[-2:] if fy_id else fields.Date.today().strftime("%y")

            department = self.env["hr.department"].browse(vals.get("department_id"))

            short_name = department.short_name

            if not short_name:
                raise ValidationError(_("Department short name is missing."))

            seq_code = f"purchase.{fiscal_year}.{short_name}"

            if not self.env['ir.sequence'].search([('code', '=', seq_code)], limit=1):
                self.env['ir.sequence'].create({
                    'name': f'Purchase {fiscal_year} {short_name}',
                    'code': seq_code,
                    'prefix': f'PO/{fiscal_year}/{short_name}/',
                    'padding': 4,
                    'number_increment': 1,
                })

            vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or _('New')

        return super().create(vals_list)
