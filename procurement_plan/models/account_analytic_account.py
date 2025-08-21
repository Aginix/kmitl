# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    procurement_plan_ids = fields.One2many('procurement.plan', 'analytic_account_id', string='Procurement Plans')
    procurement_plan_count = fields.Integer("Project Count", compute='_compute_procurement_plan_count')

    @api.depends('procurement_plan_ids')
    def _compute_procurement_plan_count(self):
        procurement_plan_data = self.env['procurement.plan']._read_group([('analytic_account_id', 'in', self.ids)], ['analytic_account_id'], ['analytic_account_id'])
        mapping = {m['analytic_account_id'][0]: m['analytic_account_id_count'] for m in procurement_plan_data}
        for account in self:
            account.procurement_plan_count = mapping.get(account.id, 0)

    @api.constrains('company_id')
    def _check_company_id(self):
        for record in self:
            if record.company_id and not all(record.company_id == c for c in record.procurement_plan_ids.mapped('company_id')):
                raise UserError(_('You cannot change the company of an analytic account if it is related to a procurement_plan.'))

    def action_view_procurement_plans(self):
        view_id = self.env.ref('procurement_plan.view_procurement_plan_tree').id
        result = {
            "type": "ir.actions.act_window",
            "res_model": "procurement.plan",
            "views": [[view_id, "tree"], [False, "form"]],
            "domain": [['analytic_account_id', '=', self.id]],
            "context": {"create": False},
            "name": _("Procurement Plans"),
        }
        if len(self.procurement_plan_ids) == 1:
            result['views'] = [(False, "form")]
            result['res_id'] = self.procurement_plan_ids.id
        return result
