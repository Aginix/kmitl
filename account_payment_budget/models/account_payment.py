# -*- coding: utf-8 -*-
# Copyright (C) 2024 KMITL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

"""
Account Payment Budget Commitment Linking

This module extends account.payment with budget commitment linking functionality.
It allows linking payments to existing budget commitments for tracking
purposes, using analytic.distribution.mixin for analytic integration.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    """
    Account Payment with Budget Commitment Linking

    Features provided:
    - Link payments to existing budget commitments
    - Auto-populate budget account from selected commitment
    - View linked budget commitment details
    - Integration with analytic distribution for tracking
    - Standard payment behavior with budget tracking integration
    """
    _name = 'account.payment'
    _inherit = ['account.payment', 'budget.commitment.mixin',
                'analytic.distribution.mixin']

    # Configure mixin field names
    _commitment_id_field = 'budget_commitment_id'
    _commitment_account_id_field = 'budget_account_id'

    # Budget Integration Fields
    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        copy=False,
        help="Related budget commitment for this payment"
    )

    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')],
        help="Budget account to be used for commitment"
    )

    @api.onchange('budget_commitment_id')
    def _onchange_budget_commitment_id(self):
        """Auto-populate budget account and analytic distribution from budget commitment"""
        if self.budget_commitment_id:
            # Auto-populate budget account
            self.budget_account_id = self.budget_commitment_id.account_id

            # Auto-populate analytic distribution from commitment's 4D analytics
            commitment = self.budget_commitment_id
            analytic_accounts = {}

            if commitment.activity_analytic_id:
                analytic_accounts[commitment.activity_analytic_id.id] = 100
                self.activity_analytic_id = commitment.activity_analytic_id
            if commitment.department_analytic_id:
                analytic_accounts[commitment.department_analytic_id.id] = 100
                self.department_analytic_id = commitment.department_analytic_id
            if commitment.fund_analytic_id:
                analytic_accounts[commitment.fund_analytic_id.id] = 100
                self.fund_analytic_id = commitment.fund_analytic_id
            if commitment.source_analytic_id:
                analytic_accounts[commitment.source_analytic_id.id] = 100
                self.source_analytic_id = commitment.source_analytic_id

            if analytic_accounts:
                self.analytic_distribution = analytic_accounts

    def action_view_budget_commitment(self):
        """View related budget commitment."""
        self.ensure_one()

        if not self.budget_commitment_id:
            raise UserError(_("No budget commitment linked to this payment"))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Commitment'),
            'res_model': 'budget.commitment',
            'res_id': self.budget_commitment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }