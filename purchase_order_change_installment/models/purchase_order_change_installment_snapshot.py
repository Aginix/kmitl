from odoo import fields, models


class PurchaseOrderChangeInstallmentSnapshot(models.Model):
    _name = "purchase.order.change.installment.snapshot"
    _description = "Installment Change Snapshot"

    change_id = fields.Many2one(
        comodel_name="purchase.order.change",
        ondelete="cascade",
        required=True,
        index=True,
    )
    snapshot_type = fields.Selection(
        selection=[
            ("before", "Before"),
            ("after", "After"),
        ],
        required=True,
    )
    installment_id = fields.Many2one(
        comodel_name="purchase.invoice.plan",
        string="Installment",
        ondelete="set null",
    )
    installment = fields.Integer(string="Installment No.")
    plan_date = fields.Date(string="Plan Date")
    duration_days = fields.Integer(string="Duration (Days)")
    percent = fields.Float(string="Percent")
    amount = fields.Monetary(string="Amount")
    deliverables = fields.Text(string="Deliverables")
    currency_id = fields.Many2one(
        related="change_id.purchase_id.currency_id",
        readonly=True,
    )
