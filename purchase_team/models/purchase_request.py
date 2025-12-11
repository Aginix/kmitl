# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    team_id = fields.Many2one(
        'purchase.team',
        string='Purchase Team',
        tracking=True,
        index=True,
        domain="[('department_id', '=', department_id), ('assign_on_pr', '=', True)]",
        help='Purchase team responsible for this request'
    )

    is_user_in_team = fields.Boolean(
        string='Is User in Team',
        compute='_compute_is_user_in_team',
        store=False
    )

    @api.depends('team_id.member_ids', 'team_id.user_id')
    def _compute_is_user_in_team(self):
        current_user = self.env.user
        for pr in self:
            pr.is_user_in_team = (
                current_user in (pr.team_id.member_ids | pr.team_id.user_id)
                if pr.team_id else False
            )
