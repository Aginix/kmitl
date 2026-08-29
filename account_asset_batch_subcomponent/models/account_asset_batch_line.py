# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatchLine(models.Model):
    _inherit = 'account.asset.batch.line'

    subcomponent_ids = fields.One2many(
        'account.asset.batch.subcomponent',
        'batch_line_id',
        string='Subcomponents'
    )

    def action_open_subcomponent_wizard(self):
        self.ensure_one()
        return {
            'name': _('Add Subcomponents'),
            'type': 'ir.actions.act_window',
            'res_model': 'batch.subcomponent.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_line_id': self.id,
            }
        }