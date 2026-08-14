# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    is_asset_number_editable = fields.Boolean(
        string="Is Asset Number Editable",
        compute='_compute_is_asset_number_editable',
        default=False
    )

    has_asset_number = fields.Boolean(
        string="Has Asset Number",
        compute="_compute_has_asset_number",
        store=True
    )

    def _compute_is_asset_number_editable(self):
        for rec in self:
            rec.is_asset_number_editable = False

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
                seq = self.env['ir.sequence'].sudo().create({
                    'name': f"account.asset.{fiscal_year}.{short_name}.{asset.gpsc_id.code}",
                    'code': seq_code,
                    'padding': 5,
                    'number_increment': 1,
                    'number_next_actual': 1,
                })

            sequence_number = self.env['ir.sequence'].next_by_code(seq_code)
            number = f"{fiscal_year}{short_name}{asset.gpsc_id.code}-{sequence_number}"
            asset.number = number

    def action_force_confirm(self):
        """Force-confirm (draft → open) an asset whose auto-numbering failed due
        to missing department/GPSC/FY. Sets a TEMP-<id> placeholder number if
        needed, then calls validate(). Admin ERP only."""
        for asset in self:
            if asset.state != "draft":
                continue
            if not asset.has_asset_number:
                asset.sudo().write({"number": "TEMP-%d" % asset.id})
            asset.validate()
            asset.message_post(
                body=_(
                    "Force Confirm (admin): confirmed by <b>%(user)s</b>."
                    " Asset number may be a placeholder — update department/GPSC/FY"
                    " and re-run Create Asset Number.",
                    user=self.env.user.name,
                ),
                subtype_xmlid="mail.mt_note",
            )

    @api.constrains('number')
    def _check_number_unique(self):
        for record in self:
            if record.number and self.search_count([('number', '=', record.number), ('id', '!=', record.id)]):
                raise ValidationError(_("Asset Number must be unique."))

    @api.depends('number')
    def _compute_has_asset_number(self):
        for rec in self:
            rec.has_asset_number = bool(rec.number)
