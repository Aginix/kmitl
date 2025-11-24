# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_type_id = fields.Many2one(
        comodel_name='res.partner.type',
        string='Partner Type',
        tracking=True,
    )

    @api.depends('partner_type_id')
    def _compute_company_type(self):
        super()._compute_company_type()
        for partner in self:
            if partner.partner_type_id:
                partner.company_type = partner.partner_type_id.company_type

    @api.onchange('partner_type_id')
    def _onchange_partner_type_id(self):
        for partner in self:
            if partner.partner_type_id:
                if partner.partner_type_id.property_account_payable_id:
                    partner.property_account_payable_id = partner.partner_type_id.property_account_payable_id.id
                if partner.partner_type_id.property_account_receivable_id:
                    partner.property_account_receivable_id = partner.partner_type_id.property_account_receivable_id.id