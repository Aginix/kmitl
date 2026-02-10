from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class BudgetCommitmentAmountWizard(models.TransientModel):
    """Wizard for obligating or consuming budget from a commitment."""

    _name = "budget.commitment.amount.wizard"
    _description = "Budget Commitment Amount Wizard"

    commitment_id = fields.Many2one(
        comodel_name="budget.commitment",
        string="Commitment",
        required=True,
        readonly=True,
    )

    wizard_type = fields.Selection(
        selection=[
            ("obligate", "Obligate"),
            ("consume", "Consume"),
        ],
        string="Type",
        required=True,
        readonly=True,
    )

    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        related="commitment_id.currency_id",
    )

    remaining_amount = fields.Monetary(
        related="commitment_id.remaining_amount",
        string="Remaining Amount",
    )

    def action_confirm(self):
        """Execute the obligate or consume action."""
        self.ensure_one()
        if self.amount <= 0:
            raise ValidationError(_("Amount must be greater than zero."))
        if self.amount > self.remaining_amount:
            raise ValidationError(
                _("Amount (%.2f) exceeds remaining amount (%.2f).")
                % (self.amount, self.remaining_amount)
            )
        commitment = self.commitment_id
        if self.wizard_type == "obligate":
            commitment.add_obligate_lines(
                self._prepare_obligate_lines_data()
            )
        else:
            consume_lines = commitment.consume(self.amount)
            for line in consume_lines:
                line.post_line()
        return {"type": "ir.actions.act_window_close"}

    def _prepare_obligate_lines_data(self):
        """Distribute amount proportionally across reserve lines."""
        reserve_lines = self.commitment_id.line_ids.filtered(
            lambda l: l.line_type == "reserve" and l.amount > 0
        )
        if not reserve_lines:
            raise UserError(_("No reserve lines found."))
        total = sum(reserve_lines.mapped("amount"))
        result = []
        distributed = 0.0
        for i, rline in enumerate(reserve_lines):
            if i == len(reserve_lines) - 1:
                line_amount = self.amount - distributed
            else:
                line_amount = round(
                    self.amount * (rline.amount / total), 2
                )
                distributed += line_amount
            if line_amount > 0:
                result.append({
                    "account_id": rline.account_id.id,
                    "amount": line_amount,
                    "analytic_distribution": rline.analytic_distribution,
                })
        return result
