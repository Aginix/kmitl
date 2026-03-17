from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AdvancePaymentUsageWizard(models.TransientModel):
    """Wizard to create a usage record for an advance payment."""

    _name = "advance.payment.usage.wizard"
    _description = "Advance Payment Usage Wizard"

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

    amount = fields.Monetary(string="Amount", required=True)

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.today,
    )

    note = fields.Text(string="Note")

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
    )

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Amount must be greater than zero."))
            if rec.amount > rec.agreement_id.amount_remaining:
                raise ValidationError(
                    _(
                        "Amount (%(amount)s) exceeds remaining balance (%(remaining)s).",
                        amount=rec.amount,
                        remaining=rec.agreement_id.amount_remaining,
                    )
                )

    def action_create_usage(self):
        """Create usage line and re-link attachments."""
        self.ensure_one()
        if self.agreement_id.state != "in_progress":
            raise UserError(_("Usage can only be recorded for in-progress agreements."))
        line = self.env["advance.payment.usage.line"].create(
            {
                "agreement_id": self.agreement_id.id,
                "amount": self.amount,
                "date": self.date,
                "note": self.note,
            }
        )
        if self.attachment_ids:
            self.attachment_ids.write(
                {
                    "res_model": "advance.payment.usage.line",
                    "res_id": line.id,
                }
            )
        return {"type": "ir.actions.act_window_close"}
