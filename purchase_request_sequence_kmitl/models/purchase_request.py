# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    @api.model
    def create(self, vals):
        if vals.get("operating_unit_id"):
            ou = self.env["operating.unit"].browse(vals["operating_unit_id"])
            if ou.department_id:
                vals["department_id"] = ou.department_id.id

        fy_id = self.env["account.fiscal.year"].browse(vals.get("date_range_fy_id"))
        fiscal_year = fy_id.name[-2:] if fy_id else fields.Date.today().strftime("%y")

        department = self.env["hr.department"].browse(vals.get("department_id"))
        short_name = department.short_name or "XXX"

        if not self.env['ir.sequence'].search([('code', 'like', f"purchase.request.{fiscal_year}.{short_name}")]):
            self.env['ir.sequence'].create({
                'name': f'Purchase Request {fiscal_year} {short_name}',
                'code': f'purchase.request.{fiscal_year}.{short_name}',
                'prefix': f'PR/{fiscal_year}/{short_name}/',
                'padding': 4,
                'number_increment': 1,
            })

        sequence = self.env['ir.sequence'].next_by_code(f"purchase.request.{fiscal_year}.{short_name}") or _('New')
        vals['name'] = sequence
        record = super().create(vals)

        if record.operating_unit_id and record.operating_unit_id.department_id:
            record.department_id = record.operating_unit_id.department_id.id
        return record
