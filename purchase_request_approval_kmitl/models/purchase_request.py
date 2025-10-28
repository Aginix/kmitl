# -*- coding: utf-8 -*-
from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'
    _state_from = ["to_verify", "to_approve"]

    _STATES = [
        ("to_verify", "To be verified"),
        ("to_approve",)
    ]

    is_purchase_request = fields.Boolean(compute="_compute_is_purchase_request")
    state = fields.Selection(
        selection_add=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        ondelete={
        "to_verify": "set default",
        }
    )
    can_edit_budget = fields.Boolean(
        compute="_compute_can_edit_budget",
    )
    can_request = fields.Boolean(compute="_compute_can_request")

    def _compute_is_purchase_request(self):
        for rec in self:
            rec.is_purchase_request = rec._name == "purchase.request"

    def _add_tier_validation_buttons(self, node, params):
        """"close btn"""
        if self.is_purchase_request:
            str_element = self.env["ir.qweb"]._render(
                "base_tier_validation.tier_validation_buttons", params
            )
            new_node = etree.fromstring(str_element)
            return new_node
        return etree.Element("div")

    def _validate_tier(self, tiers=False):
        super()._validate_tier(tiers)
        reviews = self.review_ids.filtered(
            lambda r: r.status == "pending" and (self.env.user in r.reviewer_ids)
        )
        if not reviews:
            return self.write({'state': 'approved'})

    @api.model
    def _get_after_validation_exceptions(self):
        res = super()._get_after_validation_exceptions()
        res.append("state")
        res.append("substate_id")
        return res

    def button_to_verify(self):
        self.ensure_one()
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        self.write({"state": "to_verify"})

    @api.depends("state")
    def _compute_is_editable(self):
        res = super()._compute_is_editable()
        for record in self:
            if record.state in ("to_verify"):
                record.is_editable = False

    def request_validation(self):
        self.ensure_one()
        res = super().request_validation()
        self.write({"state": "to_approve"})
        return res

    def restart_validation(self):
        self.ensure_one()
        res = super().restart_validation()
        self.write({"state": "to_verify"})
        return res

    @api.model
    def _get_under_validation_exceptions(self):
        res = super()._get_under_validation_exceptions()
        res.append("state")
        res.append("substate_id")
        return res

    @api.depends("state")
    @api.depends_context("uid")
    def _compute_can_edit_budget(self):
        user_in_group = self.env.user.has_group(
            "budget.group_budget_commitment"
        )
        for rec in self:
            rec.can_edit_budget = bool(
                user_in_group and rec.substate_sequence == 10 or rec.state == 'draft'
            )

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

    @api.depends("requested_by")
    def _compute_can_request(self):
        current_user = self.env.user
        is_manager = current_user.has_group("purchase_request.group_purchase_request_manager")
        for rec in self:
            rec.can_request = (rec.requested_by.id == current_user.id) or is_manager
