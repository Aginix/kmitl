# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "budget.commitment.mixin",
                "analytic.distribution.mixin"]

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
    @api.depends("date", "auto_post", "state")
    def _compute_hide_post_button(self):
        """Show Post button only when state=submitted.

        Draft entries must be submitted (locked) before posting.
        """
        super()._compute_hide_post_button()
        for move in self:
            if move.state == "submitted":
                move.hide_post_button = False
            else:
                move.hide_post_button = True

    # --- Actions ---
    def action_submit(self):
        """Submit (lock) the journal entry; assign sequence number."""
        for move in self:
            if move.state != "draft":
                raise UserError(_("Only draft entries can be submitted."))
        self.write({"state": "submitted"})
        # Assign sequence number on submit
        for move in self.sorted(lambda m: (m.date, m.ref or "", m.id)):
            if not move.name or move.name == "/":
                move._set_next_sequence()
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

    # --- Budget validation ---
    def _check_analytic_distribution_complete(self):
        """Validate that all required analytic dimensions are present."""
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

    def _post(self, soft=True):
        """Validate budget and auto-fill tax invoices."""
        for move in self:
            payment = move.payment_id
            if payment and payment.payment_type == "outbound":
                move._check_analytic_distribution_complete()
        self._auto_fill_tax_invoice()
        res = super()._post(soft=soft)
        return res

    def _auto_fill_tax_invoice(self):
        """Auto-fill tax_invoice_number and tax_invoice_date from the bill."""
        for move in self:
            if not hasattr(move, "tax_invoice_ids"):
                continue
            for tax_inv in move.tax_invoice_ids:
                if not tax_inv.tax_invoice_number:
                    ref = move.ref or (move.name if move.name != "/" else False)
                    if ref:
                        tax_inv.tax_invoice_number = ref
                if not tax_inv.tax_invoice_date:
                    tax_inv.tax_invoice_date = move.date

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

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if move.analytic_distribution:
                lines_without = move.line_ids.filtered(
                    lambda l: not l.analytic_distribution
                )
                if lines_without:
                    lines_without.write(
                        {"analytic_distribution": move.analytic_distribution}
                    )
        # Auto-submit vendor bills when caller requests it (e.g., DR flow)
        if self.env.context.get("auto_submit_on_create"):
            bills_to_submit = moves.filtered(
                lambda m: m.move_type in ("in_invoice", "in_refund")
                and m.state == "draft"
            )
            if bills_to_submit:
                bills_to_submit.action_submit()
        return moves

    def _inverse_analytic_distribution(self):
        """Propagate analytic distribution to convenience fields and lines."""
        super()._inverse_analytic_distribution()
        for move in self:
            if move.analytic_distribution:
                move.line_ids.write(
                    {"analytic_distribution": move.analytic_distribution}
                )

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        """When change analytic distribution, propagate to all move lines."""
        if self.analytic_distribution:
            self.line_ids.update(
                {"analytic_distribution": self.analytic_distribution}
            )
