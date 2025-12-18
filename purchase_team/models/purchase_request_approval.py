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
        domain="[('assign_on_pa', '=', True)]",
        help='Purchase team responsible for this request'
    )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        
        if rec.team_id:
            rec.team_id.assign_activity_to_team(
                rec,
                summary=_('Purchase Approval %(name)s needs review', name=rec.name)
            )
        
        return rec