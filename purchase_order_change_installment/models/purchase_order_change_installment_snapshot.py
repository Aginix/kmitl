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
        string="งวดงาน",
        ondelete="set null",
    )
    installment = fields.Integer(string="งวดที่")
    plan_date = fields.Date(string="กำหนดวันส่ง")
    duration_days = fields.Integer(string="จำนวนวัน")
    percent = fields.Float(string="สัดส่วน (%)")
    amount = fields.Monetary(string="จำนวนเงิน")
    deliverables = fields.Text(string="รายละเอียดงาน")
    currency_id = fields.Many2one(
        related="change_id.purchase_id.currency_id",
        readonly=True,
    )
