# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetSubcomponent(models.Model):
    _name = 'account.asset.subcomponent'
    _description = 'AccountAssetSubcomponent'

    sequence = fields.Integer(
        default=lambda self: self._default_sequence()
    )

    asset_id = fields.Many2one(
        "account.asset",
        required=True,
        tracking=True,
        ondelete="cascade"
    )

    name = fields.Char(
        required=True,
        tracking=True
    )

    number = fields.Char(
        compute="_compute_number",
        store=True
    )

    def _default_sequence(self):
        asset_id = self.env.context.get("default_asset_id")
        if not asset_id:
            return 1
        
        subcomponents = self.env['account.asset.subcomponent'].search([
            ('asset_id', '=', asset_id)
        ])
        count = len(subcomponents)
        return count + 1

    @api.depends("asset_id.number", "sequence")
    def _compute_number(self):
        for rec in self:
            if rec.asset_id and rec.asset_id.number:
                rec.number = f"{rec.asset_id.number} ({rec.sequence})"
            else:
                rec.number = f"({rec.sequence})"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'sequence' not in vals or not vals['sequence']:
                asset_id = vals.get('asset_id')
                if asset_id:
                    self = self.with_context(default_asset_id=asset_id)
                    vals['sequence'] = self._default_sequence()
        
        return super().create(vals_list)