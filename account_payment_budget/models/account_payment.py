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
    - Simple budget tracking integration for payments
    """
    _name = 'account.payment'
    _inherit = ['account.payment','budget.commitment.mixin']

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

    def _check_analytic_distribution_complete(self):
        required_plan_codes = {"activities", "departments", "funds", "sources"}
        if not self.analytic_distribution:
            raise ValidationError(_("Analytic distribution is required."))
        account_ids = [int(k) for k in self.analytic_distribution.keys()]
        accounts = self.env["account.analytic.account"].browse(account_ids)
        present_codes = set(accounts.mapped("root_plan_id.code"))
        missing = required_plan_codes - present_codes
        if missing:
            raise ValidationError(
                _("Missing required analytic dimensions: %s")
                % ", ".join(missing)
            )

    def action_post(self):
        for payment in self:
            if payment.payment_type == "outbound":
                payment._check_analytic_distribution_complete()
            if payment.budget_commitment_id and payment.payment_type == "outbound":
                payment._consume_commitment(amount=payment.amount)

        return super().action_post()
