# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "budget.commitment.mixin",
                "analytic.distribution.mixin"]

    # Tier validation: submitted -> posted
    _state_from = ["submitted"]
    _state_to = ["posted"]

    # Budget commitment mixin configuration
    _commitment_id_field = "budget_commitment_id"
    _commitment_account_id_field = "budget_account_id"

    # --- State ---
    state = fields.Selection(
        selection_add=[("submitted", "Submitted"), ("posted",)],
        ondelete={"submitted": "set default"},
    )

    # --- Budget fields ---
    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        copy=False,
        help="Related budget commitment for this journal entry",
    )
    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        help="Budget account to be used for commitment",
    )

    # --- Compute ---
    @api.depends("date", "auto_post", "state", "validation_status")
    def _compute_hide_post_button(self):
        """Show Post button only when submitted AND validated."""
        super()._compute_hide_post_button()
        for move in self:
            if move.validation_status == "validated" and move.state == "submitted":
                move.hide_post_button = False
            else:
                move.hide_post_button = True

    # --- Actions ---
    def action_submit(self):
        """Submit the journal entry and auto-trigger tier validation."""
        for move in self:
            if move.state != "draft":
                raise UserError(_("Only draft entries can be submitted."))
            move.state = "submitted"
        for move in self:
            if move.need_validation and move.state == "submitted":
                move.request_validation()
        return True

    def action_draft(self):
        """Reset journal entry from submitted back to draft."""
        for move in self:
            if move.state != "submitted":
                raise UserError(
                    _("Only submitted entries can be reset to draft.")
                )
            move.state = "draft"
        return True

    def action_view_budget_commitment(self):
        """View related budget commitment."""
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError(
                _("No budget commitment linked to this journal entry")
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Commitment"),
            "res_model": "budget.commitment",
            "res_id": self.budget_commitment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    # --- Onchange ---
    @api.onchange("budget_commitment_id")
    def _onchange_budget_commitment_id(self):
        """Auto-populate budget account and analytic distribution
        from budget commitment."""
        if self.budget_commitment_id:
            self.budget_account_id = self.budget_commitment_id.account_id
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
