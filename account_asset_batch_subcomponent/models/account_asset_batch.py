# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatch(models.Model):
    _inherit = 'account.asset.batch'

    def action_register_assets(self):
        res = super().action_register_assets()

        asset_model = self.env['account.asset']
        sub_model = self.env['account.asset.subcomponent']

        for batch in self:
            assets = asset_model.search([
                ('batch_id', '=', batch.id)
            ])

            for line in batch.line_ids:
                line_assets = assets.filtered(lambda a: a.batch_line_id.id == line.id)

                for asset in line_assets:
                    for sub in line.subcomponent_ids:
                        sub_model.create({
                            'asset_id': asset.id,
                            'name': sub.name,
                            'sequence': sub.sequence,
                        })

        return res
