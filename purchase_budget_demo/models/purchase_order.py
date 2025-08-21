# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = [
        "purchase.order",
        "analytic.distribution.mixin",
        "budget.commitment.mixin",
    ]

    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        readonly=True,
        copy=False,
        help="Related budget commitment for this purchase order",
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        help="Budget account to be used for commitment",
    )

    # Budget status display
    budget_status = fields.Selection(
        selection=[
            ("not_checked", "Not Checked"),
            ("sufficient", "Budget Available"),
            ("warning", "Low Budget"),
            ("insufficient", "Insufficient Budget"),
            ("committed", "Budget Committed"),
        ],
        string="Budget Status",
        compute="_compute_budget_status",
        store=True,
    )

    budget_available = fields.Monetary(
        string="Available Budget",
        compute="_compute_budget_status",
        currency_field="currency_id",
    )

    def action_reserve_budget(self):
        """Reserve budget by creating commitment"""
        self.ensure_one()

        if self.budget_commitment_id:
            raise UserError(
                _("Budget has already been reserved for this purchase order")
            )

        if not self.budget_account_id:
            raise ValidationError(_("Please specify budget account"))

        # Validate required analytic dimensions
        if not all(
            [
                self.budget_account_id,
                self.activity_analytic_id,
                self.fund_analytic_id,
                self.department_analytic_id,
                self.source_analytic_id,
            ]
        ):
            raise ValidationError(
                _("Please specify financial dimensions for budget commitment")
            )

        # Check budget availability first
        check_result = self._check_budget_availability(
            amount=self.amount_total,
            budget_account_id=self.budget_account_id.id,
            activity_analytic_id=self.activity_analytic_id.id,
            fund_analytic_id=self.fund_analytic_id.id,
            department_analytic_id=self.department_analytic_id.id,
            source_analytic_id=self.source_analytic_id.id,
        )

        if not check_result["is_sufficient"]:
            raise UserError(
                _("Cannot reserve budget due to insufficient funds: %s")
                % check_result["message"]
            )

        try:
            # Create commitment using manual parameters
            commitment = self._create_budget_commitment(
                amount=self.amount_total,
                budget_account_id=self.budget_account_id.id,
                activity_analytic_id=self.activity_analytic_id.id,
                fund_analytic_id=self.fund_analytic_id.id,
                department_analytic_id=self.department_analytic_id.id,
                source_analytic_id=self.source_analytic_id.id,
                ref=self.name,
                description=f"Purchase Order: {self.name}\nVendor: {self.partner_id.name}",
                date=self.date_order,
                auto_reserve=True,
            )

            self.budget_commitment_id = commitment

            self.message_post(
                body=_("Budget reserved: %s for amount %s")
                % (commitment.name, self.amount_total)
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Budget Reserved"),
                    "message": _("Budget has been successfully reserved for %s")
                    % self.amount_total,
                    "type": "success",
                    "sticky": False,
                },
            }

        except UserError as e:
            raise UserError(_("Cannot reserve budget: %s") % str(e))
