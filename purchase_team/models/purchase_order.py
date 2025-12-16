# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    team_id = fields.Many2one(
        'purchase.team',
        string='Purchase Team',
        tracking=True,
        index=True,
        domain="[('assign_on_po', '=', True)]",
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
        for po in self:
            po.is_user_in_team = (
                current_user in (po.team_id.member_ids | po.team_id.user_id)
                if po.team_id else False
            )