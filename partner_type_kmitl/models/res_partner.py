# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    attachment_ids = fields.One2many(
        "ir.attachment", "res_id", string="Document Attachments", tracking=True,
    )
    partner_type_id = fields.Many2one(
        comodel_name='res.partner.type', string='Partner Type', tracking=True,
    )

    @api.model
    def _default_partner_type_id(self, company_type):
        xmlid = (
            'partner_type_kmitl.partner_type_company'
            if company_type == 'company'
            else 'partner_type_kmitl.partner_type_other'
        )
        return self.env.ref(xmlid).id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'partner_type_id' not in vals:
                # company_type is "only an interface field" per core's own
                # comment on res.partner; derive from is_company when the
                # caller didn't pass company_type explicitly.
                company_type = vals.get('company_type') or (
                    'company' if vals.get('is_company') else 'person'
                )
                vals['partner_type_id'] = self._default_partner_type_id(company_type)
        return super().create(vals_list)

    @api.depends('is_company', 'partner_type_id')
    def _compute_company_type(self):
        super()._compute_company_type()
        for partner in self:
            if partner.partner_type_id:
                partner.company_type = partner.partner_type_id.company_type
