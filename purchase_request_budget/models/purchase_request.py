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
        help="Related budget commitment for this purchase request"
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
        amount = sum(self.line_ids.mapped("estimated_cost"))
        if not all([
            self.budget_account_id,
            self.activity_analytic_id,
            self.department_analytic_id,
            self.fund_analytic_id,
            self.source_analytic_id,
        ]):
            raise UserError(_("Please specify budget account and all required analytic dimensions"))

        result = self._check_budget_availability(
            amount=amount,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )

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

    def _action_purchase_reserve(self):
        self.ensure_one()
        substate = self.env["base.substate"].search(
            [("model", "=", "purchase.request"), ("sequence", "=", 20)], limit=1
        )
        self.substate_id = substate.id
        self.verified_by = self.env.user.id
        self.date_verified = fields.Date.context_today(self)

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()
        amount = sum(self.line_ids.mapped("estimated_cost"))

        if not self.budget_account_id:
            raise ValidationError(_("Please specify budget account"))

        if not all([self.activity_analytic_id, self.department_analytic_id, self.fund_analytic_id, self.source_analytic_id]):
            raise ValidationError(_("Please specify analytic dimensions for budget commitment"))

        check_result = self._check_budget_availability(
            amount=amount,
            activity_analytic_id=self.activity_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )

        if not check_result['is_sufficient']:
            raise UserError(_("Cannot reserve budget due to insufficient funds: %s") % check_result['message'])

        try:
            commitment = self._create_budget_commitment(
                amount=amount,
                activity_analytic_id=self.activity_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.name,
                description=f"Purchase Request: {self.name}\\nVendor: {self.title}",
                date=self.date_start,
                auto_reserve=True
            )
            self.message_post(body=_("Budget reserved: %s for amount %s") % (commitment.name, amount))
            self._action_purchase_reserve()
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.request",
                "view_mode": "form",
                "res_id": self.id,
                "target": "current",
                "context": self.env.context,
            }

        except UserError as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))

    def button_draft(self):
        for request in self:
            if request.budget_commitment_id:
                try:
                    request._cancel_budget_commitment()
                    request.write({"verified_by": "", "date_verified": False})
                    request.message_post(body=_("Budget commitment %s has been cancelled") % request.budget_commitment_id.name)
                except UserError as e:
                    request.message_post(body=_("Warning: Could not cancel budget commitment: %s") % str(e))

        return super().button_draft()

    def button_rejected(self):
        for request in self:
            if request.budget_commitment_id:
                try:
                    request._cancel_budget_commitment()
                    request.message_post(body=_("Budget commitment %s has been cancelled") % request.budget_commitment_id.name)
                except UserError as e:
                    request.message_post(body=_("Warning: Could not cancel budget commitment: %s") % str(e))

        return super().button_rejected()
