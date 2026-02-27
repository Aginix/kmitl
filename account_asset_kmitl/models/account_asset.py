# -*- coding: utf-8 -*-
import random
import string

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


def _generate_random_code(length=8):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


class AccountAsset(models.Model):
    _name = "account.asset"
    _inherit = ["account.asset", "portal.mixin", "analytic.mixin"]

    _analytic_keys = {
        "sources": "source_analytic_id",
        "departments": "department_analytic_id",
        "funds": "fund_analytic_id",
        "activities": "activity_analytic_id",
    }

    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="แหล่งเงิน",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("sources"),
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "sources")],
    )
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ส่วนงาน",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("departments"),
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "departments")],
    )

    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="กองทุน",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("funds"),
        domain=[("root_plan_id.code", "=", "funds")],
        store=True,
        readonly=False,
    )

    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="ด้าน/แผนงาน/กิจกรรม",
        compute="_compute_analytic_id",
        inverse=lambda self: self._update_analytic_distribution("activities"),
        store=True,
        readonly=False,
        domain=[("root_plan_id.code", "=", "activities")],
    )

    account_fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal year"
    )

    gpsc_id = fields.Many2one(
        "procurement.gpsc",
        string="GPSC Id"
    )

    department_id = fields.Many2one(
        "hr.department",
        string="Department"
    )

    def _default_access_uid(self):
        return _generate_random_code(8)

    access_uid = fields.Char(
        string="Access Code",
        default=_default_access_uid,
        size=8,
        copy=False,
    )

    barcode_value = fields.Char(
        string="Barcode Value",
        compute="_compute_barcode_value",
        store=False,
    )

    def _compute_barcode_value(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.barcode_value = f"{base_url}{rec.access_url}"

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
        	rec.access_url = f"/account_assets/{rec.access_uid}"

    def action_open_portal_view(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = f"{base_url}{self.access_url}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "self",
        }
