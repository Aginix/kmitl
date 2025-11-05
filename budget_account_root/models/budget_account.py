# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAccount(models.Model):
    _inherit = 'budget.account'

    root_id = fields.Many2one(
        "budget.account",
        compute="_compute_root_id",
        string="Top Parent Analytic Account",
        store=True,
        recursive=True,
    )

    def _get_root_id(self):
        self.ensure_one()
        if self.parent_id:
            return self.parent_id._get_root_id()
        else:
            return self

    @api.depends("parent_id", "parent_id.root_id")
    def _compute_root_id(self):
        for account in self:
            account.root_id = account._get_root_id()
