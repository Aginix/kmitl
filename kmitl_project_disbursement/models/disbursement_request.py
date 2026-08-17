# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    # A disbursement belongs to a project through the ``kmitl_project`` dimension
    # carried in its ``analytic_distribution`` (a project is spent down by its own
    # purchase requests and disbursements — see kmitl_project CONTEXT.md). Mirror
    # that dimension into a stored column so the project can search/count its
    # disbursements exactly like it does its budget move lines. The JSON
    # distribution stays the source of truth; this is a read-only lookup.
    kmitl_project_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="โครงการ/กิจกรรม",
        compute="_compute_kmitl_project_analytic_id",
        store=True,
        domain=[("root_plan_id.code", "=", "kmitl_project")],
    )

    @api.depends("analytic_distribution")
    def _compute_kmitl_project_analytic_id(self):
        for rec in self:
            account_ids = [int(a) for a in rec.analytic_distribution or {}]
            accounts = self.env["account.analytic.account"].browse(account_ids)
            rec.kmitl_project_analytic_id = accounts.filtered(
                lambda a: a.plan_id.code == "kmitl_project"
            )[:1]
