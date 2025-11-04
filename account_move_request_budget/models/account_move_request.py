from odoo import _, api, fields, models


class AccountMoveRequest(models.Model):

    _name = 'account.move.request'
    _inherit = ['account.move.request', 'budget.commitment.mixin']

    _commitment_id_field = 'budget_commitment_id'
    _commitment_account_id_field = 'budget_account_id'

    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        copy=False,
    )

    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')],
        copy=False,
    )

    analytic_distribution = fields.Json(
        copy=False,
    )

    @api.onchange('budget_commitment_id')
    def _onchange_budget_commitment_id(self):
        if self.budget_commitment_id:
            budget = self.budget_commitment_id
            self.budget_account_id = budget.account_id
            self.analytic_distribution = budget.analytic_distribution

            for line in self.line_ids:
                line.analytic_distribution = budget.analytic_distribution
