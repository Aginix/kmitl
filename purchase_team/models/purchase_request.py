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
        domain="[('assign_on_pr', '=', True)]",
        help='Purchase team responsible for this request'
    )

    def button_to_approve(self):
        res = super().button_to_approve()
        
        for rec in self:
            if rec.team_id:
                rec.team_id.assign_activity_to_team(
                    rec,
                    summary=_('Purchase Request %(name)s ready for approval', name=rec.name)
                )
        
        return res