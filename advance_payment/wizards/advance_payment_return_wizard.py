from odoo import _, fields, models
from odoo.exceptions import UserError


class AdvancePaymentReturnWizard(models.TransientModel):
    """Wizard to confirm money return for an advance payment agreement."""

    _name = "advance.payment.return.wizard"
    _description = "Advance Payment Return Wizard"

    agreement_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Agreement",
        required=True,
        readonly=True,
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="agreement_id.currency_id",
    )

    loan_amount = fields.Monetary(
        string="Loan Amount",
        related="agreement_id.loan_amount",
        readonly=True,
    )

    amount_used = fields.Monetary(
        string="Amount Used",
        related="agreement_id.amount_used",
        readonly=True,
    )

    amount_remaining = fields.Monetary(
        string="Amount Remaining",
        related="agreement_id.amount_remaining",
        readonly=True,
    )

    def action_confirm_return(self):
        """Close the agreement (in_progress → done)."""
        self.ensure_one()
        if self.agreement_id.state != "in_progress":
            raise UserError(
                _("Only in-progress agreements can be closed.")
            )
        self.agreement_id.action_close()
        return {"type": "ir.actions.act_window_close"}
