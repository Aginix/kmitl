# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    subcomponent_ids = fields.One2many(
        "account.asset.subcomponent",
        "asset_id",
        string="Subcomponents",
        tracking=True
    )

    def create_asset_number(self):
        for asset in self:
            if asset.has_asset_number:
                continue

            if not (asset.department_id and asset.gpsc_id and asset.account_fiscal_year_id):
                raise ValidationError(_("Missing department or GPSC or Fiscal year."))

            fiscal_year = str(asset.account_fiscal_year_id.name)[-2:]
            short_name = asset.department_id.short_name

            if not short_name:
                raise ValidationError(_("Department short name is missing."))

            seq_code = f"account.asset.{fiscal_year}.{short_name}.{asset.gpsc_id.code}"
            seq = self.env['ir.sequence'].sudo().search([('code', '=', seq_code)], limit=1)

            if not seq:
                try:
                    seq = self.env['ir.sequence'].sudo().create({
                        'name': seq_code,
                        'code': seq_code,
                        'padding': 5,
                        'number_increment': 1,
                        'number_next_actual': 1,
                    })
                except Exception:
                    seq = self.env['ir.sequence'].sudo().search(
                        [('code', '=', seq_code)], limit=1
                    )
                if not seq:
                    raise UserError(
                        _("Failed to create or find sequence %s") % seq_code
                    )

            sequence_number = self.env['ir.sequence'].next_by_code(seq_code)

            number = f"{fiscal_year}{short_name}{asset.gpsc_id.code}-{sequence_number}"
            if asset.subcomponent_ids:
                number += " (1)"

            asset.number = number

            if asset.subcomponent_ids:
                for idx, subcomp in enumerate(asset.subcomponent_ids.sorted('id'), start=2):
                    subcomp.sequence = idx

    def _update_number_by_subcomponent(self):
        for asset in self:
            if not asset.number:
                continue
            if asset.subcomponent_ids and not asset.number.endswith(" (1)"):
                asset.number += " (1)"
            elif not asset.subcomponent_ids and asset.number.endswith(" (1)"):
                asset.number = asset.number[:-4]
    