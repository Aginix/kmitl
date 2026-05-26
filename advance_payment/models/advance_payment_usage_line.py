from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AdvancePaymentUsageLine(models.Model):
    """Usage record line for advance payment agreements."""

    _name = "advance.payment.usage.line"
    _description = "Advance Payment Usage Line"
    _order = "date desc, id desc"

    agreement_id = fields.Many2one(
        comodel_name="advance.payment",
        string="Agreement",
        required=True,
        ondelete="cascade",
    )

    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="agreement_id.currency_id",
        store=True,
    )

    amount = fields.Monetary(string="Amount", required=True)

    @api.constrains("amount", "agreement_id")
    def _check_total_not_exceeding(self):
        for rec in self:
            agreement = rec.agreement_id
            total_used = sum(agreement.usage_line_ids.mapped("amount"))
            total_returned = sum(
                agreement.return_line_ids.filtered(
                    lambda l: l.state == "done"
                ).mapped("amount")
            )
            if total_used + total_returned > agreement.loan_amount:
                raise ValidationError(
                    _(
                        "Total usage (%(used)s) + returns (%(returned)s)"
                        " exceeds loan amount (%(loan)s).",
                        used=total_used,
                        returned=total_returned,
                        loan=agreement.loan_amount,
                    )
                )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.today,
    )

    note = fields.Text(string="Note")

    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "advance.payment.usage.line")],
    )
