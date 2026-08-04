from odoo import fields, models


class AdvancePaymentUsageLine(models.Model):
    """Usage record for an advance payment.

    Informational only: populated by integrations (e.g. advance_payment_disbursement
    creates one per disbursement request). The loan debt is driven by the
    agreement's actual_expense_amount, not by these lines. Kept as a model so the
    disbursement / operating-unit bridges can extend it.
    """

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
    date = fields.Date(string="Date", required=True, default=fields.Date.today)
    note = fields.Text(string="Note")
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        string="Attachments",
        domain=[("res_model", "=", "advance.payment.usage.line")],
    )
