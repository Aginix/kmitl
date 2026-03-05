from odoo import fields, models


class KrisProjectInstallmentAllocation(models.Model):
    _name = "kris.project.installment.allocation"
    _description = "KRIS Project Installment Allocation Breakdown"
    _order = "allocation_line_id"

    installment_id = fields.Many2one(
        comodel_name="kris.project.installment",
        string="งวดที่",
        required=True,
        ondelete="cascade",
        index=True,
    )
    allocation_line_id = fields.Many2one(
        comodel_name="kris.project.allocation.line",
        string="การจัดสรร",
        required=True,
        ondelete="cascade",
    )
    amount = fields.Monetary(string="จำนวนเงิน")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="installment_id.currency_id",
        readonly=True,
    )
