from odoo import fields, models


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
