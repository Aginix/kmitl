# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartnerType(models.Model):
    _name = 'res.partner.type'
    _description = 'ResPartnerType'

    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
    )

    company_type = fields.Selection(
        selection=[('person', 'Individual'), ('company', 'Company')],
        string='Company Type',
        required=True,
        tracking=True,
    )

    property_account_receivable_id = fields.Many2one(
        comodel_name='account.account',
        string='Account Receivable',
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        company_dependent=True,
        tracking=True,
        help='This account will be used instead of the default one as the receivable account for the partner',
    )

    property_account_payable_id = fields.Many2one(
        comodel_name='account.account',
        string='Account Payable',
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        company_dependent=True,
        tracking=True,
        help='This account will be used instead of the default one as the payable account for the partner',
    )

    partner_ids = fields.One2many(
        comodel_name='res.partner',
        inverse_name='partner_type_id',
        string='Partners',
        readonly=True,
    )

    def unlink(self):
        for record in self:
            if record.partner_ids:
                raise UserError(_("Cannot delete partner type in used."))
        return super().unlink()