# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class ResPartnerType(models.Model):
    _name = 'res.partner.type'
    _description = 'Partner Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    company_type = fields.Selection(
        selection=[('person', 'Individual'), ('company', 'Company')],
        string='Company Type', required=True, tracking=True,
    )
    partner_ids = fields.One2many(
        comodel_name='res.partner', inverse_name='partner_type_id',
        string='Partners', readonly=True,
    )

    def unlink(self):
        for record in self:
            if record.partner_ids:
                raise UserError(_("Cannot delete partner type in use."))
        return super().unlink()
