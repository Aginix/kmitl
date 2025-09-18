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
    line_ids = fields.One2many(
        comodel_name="purchase.request.line",
        inverse_name="request_id",
        string="Products to Purchase",
        copy=True,
        tracking=True,
        readonly=False,
    )

    def write(self, vals):
        if 'analytic_distribution' in vals:
            for rec in self:
                rec.line_ids.update({ 'analytic_distribution': vals['analytic_distribution']})
        return super().write(vals)

    def action_open_budget_commitment(self):
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError("ยังไม่มี Budget Commitment สำหรับเอกสารนี้")

        return {
            "type": "ir.actions.act_window",
            "name": "Budget Commitment",
            "res_model": "budget.commitment",
            "view_mode": "form",
            "res_id": self.budget_commitment_id.id,
            "target": "current",
        }

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()

        if not self.budget_account_id:
            raise ValidationError(_("Please specify budget account"))

        if not all([self.activity_analytic_id, self.department_analytic_id, self.fund_analytic_id, self.source_analytic_id]):
            raise ValidationError(_("Please specify analytic dimensions for budget commitment"))

        amount = sum(self.line_ids.mapped("estimated_cost"))

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
                description=f"Purchase Request: {self.name}",
                date=self.date_start,
                auto_reserve=True
            )
            self.message_post(body=_("Budget reserved: %s for amount %s") % (commitment.name, amount))
            self.state = 'to_approve'
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
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.write({"verified_by": "", "date_verified": False})
                    record.message_post(body=_("Budget commitment %s has been cancelled") % record.budget_commitment_id.name)
                except UserError as e:
                    record.message_post(body=_("Warning: Could not cancel budget commitment: %s") % str(e))

        return super().button_draft()

    def button_rejected(self):
        for record in self:
            if record.budget_commitment_id:
                try:
                    record._cancel_budget_commitment()
                    record.message_post(body=_("Budget commitment %s has been cancelled") % record.budget_commitment_id.name)
                except UserError as e:
                    record.message_post(body=_("Warning: Could not cancel budget commitment: %s") % str(e))

        return super().button_rejected()

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic_distribution set analytic distribution on all order lines"""
        if self.analytic_distribution:
            self.line_ids.update(
                {"analytic_distribution": self.analytic_distribution}
            )
