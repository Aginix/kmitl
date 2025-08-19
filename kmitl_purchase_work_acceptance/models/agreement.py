# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class Agreement(models.Model):
    _inherit = 'agreement'

    wa_ids = fields.One2many(
        comodel_name="work.acceptance",
        inverse_name="agreement_id",
        string="Work Acceptances",
    )

    wa_count = fields.Integer(
        string="Work Acceptance Count",
        compute="_compute_wa_count",
    )

    invoice_plan_count = fields.Integer(
        string="Invoice Plan Count",
        compute="_compute_invoice_plan_count",
    )

    wa_invoice_plan_equal = fields.Boolean(
        compute="_compute_wa_invoice_plan_equal",
        string="WA = Invoice Plan"
)
    @api.depends("wa_count", "invoice_plan_count")
    def _compute_wa_invoice_plan_equal(self):
        for rec in self:
            rec.wa_invoice_plan_equal = rec.wa_count == rec.invoice_plan_count

    @api.depends("wa_ids")
    def _compute_wa_count(self):
        for rec in self:
            rec.wa_count = len(rec.wa_ids)

    @api.depends("invoice_plan_ids")
    def _compute_invoice_plan_count(self):
        for rec in self:
            rec.invoice_plan_count = len(rec.invoice_plan_ids)

    def action_view_work_acceptances(self):
        self.ensure_one()

        action = {
            'name': 'Work Acceptances',
            'type': 'ir.actions.act_window',
            'res_model': 'work.acceptance',
            'view_mode': 'tree,form',
            'domain': [('agreement_id', '=', self.id)],
            'context': {
                'default_agreement_id': self.id,
                'default_partner_id': self.partner_id.id,
                'search_default_agreement_id': self.id,
            },
            'target': 'current',
        }

        if self.wa_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.wa_ids[0].id,
                'views': [(False, 'form')],
            })

        return action
