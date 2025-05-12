# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    hierarchy_level = fields.Integer(
        string="Level",
        compute="_compute_hierarchy_level",
        store=False,
        recursive=True,
    )

    @api.depends("parent_id.hierarchy_level")
    def _compute_hierarchy_level(self):
        for account in self:
            if account.parent_id:
                account.hierarchy_level = account.parent_id.hierarchy_level + 1
            else:
                account.hierarchy_level = 0
