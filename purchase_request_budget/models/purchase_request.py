# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _inherit = ['purchase.request', 'budget.commitment.mixin', 'analytic.distribution.mixin']

    budget_commitment_id = fields.Many2one(
        'budget.commitment',
        string='Budget Commitment',
        readonly=True,
        copy=False,
        help="Related budget commitment for this purchase order"
    )
    budget_account_id = fields.Many2one(
        'budget.account',
        string='Budget Account',
        domain=[('budgetable', '=', True), ('budget_type', '=', 'expense')],
        help="Budget account to be used for commitment"
    )

    def action_check_budget(self):
        """Action to check budget availability"""
        self.ensure_one()

        if not all([
            self.budget_account_id,
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
            self.source_analytic_id,
        ]):
            raise UserError(_("Please specify budget account and all required analytic dimensions"))

        # Check budget availability using dynamic field approach
        result = self._check_budget_availability(
            amount=sum(self.line_ids.mapped("estimated_cost")),
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )

        # Show notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Budget Check'),
                'message': result['message'],
                'type': 'success' if result['is_sufficient'] else 'warning',
                'sticky': False,
            }
        }

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()

        if self.budget_commitment_id:
            raise UserError(_("Budget has already been reserved for this purchase order"))

        if not self.budget_account_id:
            raise ValidationError(_("Please specify budget account"))

        # Validate required analytic dimensions
        if not all([self.activity_analytic_id, self.department_analytic_id, self.fund_analytic_id, self.source_analytic_id]):
            raise ValidationError(_("Please specify analytic dimensions for budget commitment"))

        # Check budget availability first
        check_result = self._check_budget_availability(
            amount=sum(self.line_ids.mapped("estimated_cost")),
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )

        if not check_result['is_sufficient']:
            raise UserError(_("Cannot reserve budget due to insufficient funds: %s") % check_result['message'])

        try:
            # Create commitment using dynamic field approach
            commitment = self._create_budget_commitment(
                amount=sum(self.line_ids.mapped("estimated_cost")),
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.name,
                description=f"Purchase Request: {self.name}\\nVendor: {self.title}",
                date=self.date_start,
                auto_reserve=True
            )
            # Note: commitment is automatically stored in budget_commitment_id by the mixin
            self.message_post(body=_("Budget reserved: %s for amount %s") % (commitment.name, sum(self.line_ids.mapped("estimated_cost"))))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Budget Reserved'),
                    'message': _('Budget has been successfully reserved for %s') % sum(self.line_ids.mapped("estimated_cost")),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except UserError as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))
