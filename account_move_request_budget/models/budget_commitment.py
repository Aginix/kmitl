# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    account_move_request_ids = fields.One2many(
        string="Account Move Requests",
        comodel_name="account.move.request",
        inverse_name="budget_commitment_id",
        copy=False,
    )

    account_move_request_count = fields.Integer(
        compute="_compute_account_move_request_count",
    )

    @api.depends("account_move_request_ids")
    def _compute_account_move_request_count(self):
        for rec in self:
            rec.account_move_request_count = len(rec.account_move_request_ids)

    def action_view_account_move_requests(self):
        self.ensure_one()
        return {
            "res_model": "account.move.request",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "view_type": "form",
            "res_id": self.account_move_request_ids[0].id,
        }
