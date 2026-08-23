# -*- coding: utf-8 -*-
from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('partner_type_id')
    def _onchange_partner_type_id(self):
        for partner in self:
            if partner.partner_type_id:
                if partner.partner_type_id.property_account_payable_id:
                    partner.property_account_payable_id = partner.partner_type_id.property_account_payable_id.id
                if partner.partner_type_id.property_account_receivable_id:
                    partner.property_account_receivable_id = partner.partner_type_id.property_account_receivable_id.id
