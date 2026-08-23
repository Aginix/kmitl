# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartnerType(models.Model):
    _inherit = 'res.partner.type'

    property_account_receivable_id = fields.Many2one(
        comodel_name='account.account', string='Account Receivable',
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        company_dependent=True, tracking=True,
        help='This account will be used instead of the default one as the receivable account for the partner',
    )
    property_account_payable_id = fields.Many2one(
        comodel_name='account.account', string='Account Payable',
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False), ('company_id', '=', current_company_id)]",
        company_dependent=True, tracking=True,
        help='This account will be used instead of the default one as the payable account for the partner',
    )
    wht_tax_id = fields.Many2one(
        comodel_name='account.withholding.tax', string='WHT',
        company_dependent=True, tracking=True,
    )
