# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    is_asset_number_editable = fields.Boolean(
        string="Is Asset Number Editable",
        compute='_compute_is_asset_number_editable',
        default=False
    )

    def _compute_is_asset_number_editable(self):
        for rec in self:
            rec.is_asset_number_editable = False

    def _create_asset_number(self):
        for asset in self:
            if not (asset.department_id and asset.gpsc_id):
                raise ValidationError(_("Missing department or GPSC."))

            fiscal_year = str(asset.account_fiscal_year_id.name)[-2:]
            short_name = asset.department_id.short_name or "XXX"
            seq_code = f"account.asset.{fiscal_year}.{short_name}.{asset.gpsc_id.code}"
            seq = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)

            if not seq:
                seq = self.env['ir.sequence'].sudo().create({
                    'name': f"account.asset.{fiscal_year}.{short_name}.{asset.gpsc_id.code}",
                    'code': seq_code,
                    'padding': 5,
                    'number_increment': 1,
                    'number_next_actual': 1,
                })

            sequence_number = self.env['ir.sequence'].next_by_code(seq_code)
            number = f"{fiscal_year}-{short_name}-{asset.gpsc_id.code}-{sequence_number}"
            asset.number = number

    def validate(self):
        res = super().validate()
        for asset in self:
            if not asset.number:
                asset._create_asset_number()
        return res