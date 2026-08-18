# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


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

    # Resolve the actual project record behind that dimension so the DR form can
    # link back to it with a smart button (its analytic account is unique per
    # project, minted once — see kmitl_project » Project Number).
    kmitl_project_id = fields.Many2one(
        "kmitl.project",
        string="โครงการ/กิจกรรม",
        compute="_compute_kmitl_project_id",
        store=True,
    )

    @api.depends("kmitl_project_analytic_id")
    def _compute_kmitl_project_id(self):
        # sudo the lookup: kmitl.project read is gated to the project groups, but
        # every disbursement officer reads DRs. Resolving the link must not depend
        # on the reader holding project access (the DR already carries the dim).
        Project = self.env["kmitl.project"].sudo()
        for rec in self:
            rec.kmitl_project_id = (
                Project.search(
                    [("analytic_account_id", "=", rec.kmitl_project_analytic_id.id)],
                    limit=1,
                )
                if rec.kmitl_project_analytic_id
                else False
            )

    def action_open_kmitl_project(self):
        self.ensure_one()
        if not self.kmitl_project_id:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "name": _("โครงการ/กิจกรรม"),
            "res_model": "kmitl.project",
            "res_id": self.kmitl_project_id.id,
            "view_mode": "form",
            "target": "current",
        }
