# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetSubcomponent(models.Model):
    _name = 'account.asset.subcomponent'
    _description = 'AccountAssetSubcomponent'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    sequence = fields.Integer(
        required=True,
        tracking=True,
        string="Sequence",
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

    @api.depends("asset_id.number", "sequence")
    def _compute_number(self):
        for rec in self:
            if rec.asset_id and rec.asset_id.number:
                base_number = rec.asset_id.number
                if base_number.endswith(" (1)"):
                    base_number = base_number[:-4]
                rec.number = f"{base_number} ({rec.sequence})"
            else:
                rec.number = f"({rec.sequence})"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            asset_id = vals.get('asset_id')
            if asset_id and ('sequence' not in vals or not vals.get('sequence')):
                existing_count = self.search_count([('asset_id', '=', asset_id)])
                vals['sequence'] = existing_count + 2

        records = super().create(vals_list)

        for rec in records:
            rec.asset_id._update_number_by_subcomponent()

        return records
    
    def unlink(self):
        asset_ids = self.mapped('asset_id')
        res = super().unlink()

        for asset in asset_ids:
            asset._update_number_by_subcomponent()

            remaining_subcomps = asset.subcomponent_ids.sorted('sequence')
            for idx, subcomp in enumerate(remaining_subcomps, start=2):
                if subcomp.sequence != idx:
                    subcomp.sequence = idx
            
        return res
    
    def write(self, vals):
        res = super().write(vals)
        if 'sequence' in vals:
            for rec in self:
                rec.asset_id._update_number_by_subcomponent()
                
        return res