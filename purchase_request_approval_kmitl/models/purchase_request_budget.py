# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    can_edit_budget = fields.Boolean(
        compute="_compute_can_edit_budget",
    )

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_can_edit_budget(self):
        user_in_group = self.env.user.has_group(
            "purchase_request_approval_kmitl.group_purchase_request_budget"
        )
        for rec in self:
            rec.can_edit_budget = bool(
                user_in_group and rec.substate_sequence == 10 or rec.state == 'draft'
            )

    def action_reserve_budget(self):
        """จองงบประมาณ"""
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
            substate = self.env["base.substate"].search(
                [("model", "=", "purchase.request"), ("sequence", "=", 20)], limit=1
            )
            self.write(
                {
                    "substate_id": substate.id,
                    "verified_by": self.env.user.id,
                    "date_verified": fields.Date.context_today(self),
                }
            )
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
