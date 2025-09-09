# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _name = 'procurement.plan'
    _inherit = ['procurement.plan']

    READONLY_STATES = {
        "validate": [("readonly", True)],
        "pending": [("readonly", True)],
        "procurement": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }
    budget_commitment_ids = fields.One2many('budget.commitment', 'procurement_plan_id', string="ผูกพันงบประมาณ", readonly=True)
    budget_commitment_count = fields.Integer(string="จำนวนผูกพันงบประมาณ", compute='_compute_budget_commitment_count')
    budget_appropriation_id = fields.Many2one('budget.appropriation', related='budget_appropriation_line_id.appropriation_id', store=True, readonly=True)
    budget_appropriation_line_id = fields.Many2one('budget.appropriation.line')
    budget_account_id = fields.Many2one('budget.account', string="รหัสงบประมาณ", states=READONLY_STATES)
    activity_analytic_id = fields.Many2one(states=READONLY_STATES)
    department_analytic_id = fields.Many2one(states=READONLY_STATES)
    fund_analytic_id = fields.Many2one(states=READONLY_STATES)
    source_analytic_id = fields.Many2one(states=READONLY_STATES)

    def _compute_budget_commitment_count(self):
        for rec in self:
            rec.budget_commitment_count = len(rec.budget_commitment_ids)

    def action_view_budget_commitment(self):
        self.ensure_one()
        action = self.env.ref('procurement_plan_budget.action_budget_commitment_procurement_plan').read()[0]
        action['domain'] = [('procurement_plan_id', '=', self.id)]
        action['context'] = {'default_procurement_plan_id': self.id}
        return action

    def action_open_budget_commitments(self):
        self.ensure_one()
        return {
            'name': 'Budget Commitments',
            'type': 'ir.actions.act_window',
            'res_model': 'budget.commitment',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('budget.budget_commitment_tree_view').id, 'tree'),
                      (False, 'form')],
            'domain': [('procurement_plan_id', '=', self.id)],
            'context': dict(self.env.context, default_procurement_plan_id=self.id),
        }
