# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    team_id = fields.Many2one(
        'purchase.team',
        string='Purchase Team',
        tracking=True,
        index=True,
        domain="[('department_id', '=', requesting_department_id), ('assign_on_pa', '=', True)]",
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
        for pa in self:
            pa.is_user_in_team = (
                current_user in (pa.team_id.member_ids | pa.team_id.user_id)
                if pa.team_id else False
            )