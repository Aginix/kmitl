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
    partner_count = fields.Integer(
        string='Partners', compute='_compute_partner_count',
    )

    def _compute_partner_count(self):
        counts = self.env['res.partner'].read_group(
            [('partner_type_id', 'in', self.ids)],
            ['partner_type_id'],
            ['partner_type_id'],
        )
        data = {row['partner_type_id'][0]: row['partner_type_id_count'] for row in counts}
        for rec in self:
            rec.partner_count = data.get(rec.id, 0)

    def action_view_partners(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('partner_type_id', '=', self.id)],
        }

    def unlink(self):
        for record in self:
            if record.with_context(active_test=False).partner_ids:
                raise UserError(_("Cannot delete partner type in use."))
        return super().unlink()
