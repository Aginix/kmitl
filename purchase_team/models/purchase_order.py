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
    
    @api.model
    def create(self, vals):
        rec = super().create(vals)

        if rec.team_id:
            rec.team_id.assign_activity_to_team(
                rec,
                summary=_('Purchase Order %(name)s created', name=rec.name)
            )
        
        return rec
    
    def write(self, vals):
        for rec in self:
            old_team = rec.team_id
            res = super().write(vals)

            new_team = rec.team_id
            if 'team_id' in vals and new_team != old_team:
                rec.activity_ids.filtered(lambda a: a.res_model == rec._name and a.res_id == rec.id).unlink()
                
                if new_team:
                    new_team.assign_activity_to_team(
                        rec,
                        summary=_('Purchase Order %(name)s needs review', name=rec.name)
                    )
        return res