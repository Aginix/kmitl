# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAssetBatch(models.Model):
    _inherit = 'account.asset.batch'

    def action_register_assets(self):
        for batch in self:
            if not batch.line_ids:
                raise ValidationError(_("Cannot register assets without any lines."))

            if any(line.amount <= 0 for line in batch.line_ids):
                raise ValidationError(_("Some lines have zero amount. Please correct them before proceeding."))

            asset_model = self.env['account.asset']
            sub_model = self.env['account.asset.subcomponent']

            for line in batch.line_ids:
                for i in range(line.amount):
                    asset = asset_model.create({
                        "name": line.name,
                        "analytic_distribution": line.analytic_distribution,
                        "date_start": batch.date,
                        "account_fiscal_year_id": batch.account_fiscal_year_id.id,
                        "operating_unit_id": batch.operating_unit_id.id,
                        "department_id": batch.department_id.id,
                        "purchase_id": batch.purchase_id.id,
                        "gpsc_id": line.gpsc_id.id,
                        "profile_id": line.profile_id.id,
                        "purchase_value": line.price_per_unit,
                        "batch_line_id": line.id,
                        "batch_id": batch.id,
                    })

                    for sub in line.subcomponent_ids:
                        sub_model.create({
                            'asset_id': asset.id,
                            'name': sub.name,
                            'sequence': sub.sequence,
                        })

            batch.state = 'done'
