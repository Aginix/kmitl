# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import _, api, fields, models


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    is_egp = fields.Boolean(string="e-GP")

    egp_project_id = fields.Char(string="เลขที่โครงการ e-GP", tracking=True)
    egp_project_url = fields.Char(
        string="ลิงค์ e-GP", compute="_compute_egp_project_url", readonly=True
    )

    @api.depends("egp_project_id")
    def _compute_egp_project_url(self):
        for record in self:
            record.egp_project_url = record.get_epg_project_url()

    def get_epg_project_url(self):
        if not self.egp_project_id:
            return False
        ts = str(datetime.now().timestamp())
        project_id = self.egp_project_id
        return f"https://process.gprocurement.go.th/egp2procmainWeb/jsp/public_announ_search.jsp?projectId={project_id}&homeflag=QR"

    @api.onchange('estimated_cost')
    def _onchange_estimated_cost(self):
        for rec in self:
            if rec.estimated_cost and rec.estimated_cost > 100000:
                rec.is_egp = True
