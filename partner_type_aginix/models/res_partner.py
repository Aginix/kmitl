# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Document Attachments",
        tracking=True,
    )

    partner_type_id = fields.Many2one(
        comodel_name='res.partner.type',
        string='Partner Type',
        tracking=True,
    )

    @api.model
    def _default_partner_type_id(self, company_type):
        if company_type == 'person':
            return self.env.ref('partner_type_aginix.partner_type_other').id
        else:
            return self.env.ref('partner_type_aginix.partner_type_company').id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "partner_type_id" not in vals:
                company_type = vals.get('company_type', 'person')
                vals['partner_type_id'] = self._default_partner_type_id(company_type)
        return super().create(vals_list)

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

    @api.depends('partner_type_id.property_account_payable_id', 'partner_type_id.property_account_receivable_id')
    def _compute_accounts_from_type(self):
        for partner in self:
            if partner.partner_type_id:
                if partner.partner_type_id.property_account_payable_id:
                    partner.property_account_payable_id = partner.partner_type_id.property_account_payable_id.id
                if partner.partner_type_id.property_account_receivable_id:
                    partner.property_account_receivable_id = partner.partner_type_id.property_account_receivable_id.id
