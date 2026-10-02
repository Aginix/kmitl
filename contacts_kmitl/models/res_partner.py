# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_erp_manager = fields.Boolean(compute="_compute_is_erp_manager")

    @api.depends_context("uid")
    def _compute_is_erp_manager(self):
        is_manager = self.env.user.has_group("base.group_erp_manager")
        for record in self:
            record.is_erp_manager = is_manager
