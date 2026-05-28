from odoo import fields, models


class KrisProjectReceiptAllocation(models.Model):
    _name = "kris.project.receipt.allocation"
    _description = "KRIS Project Receipt Allocation Breakdown"
    _order = "allocation_line_id"

    receipt_id = fields.Many2one(
        comodel_name="kris.project.receipt",
        string="Revenue",
        required=True,
        ondelete="cascade",
        index=True,
    )
    allocation_line_id = fields.Many2one(
        comodel_name="kris.project.allocation.line",
        string="Allocation",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        related="allocation_line_id.name",
        string="Allocator",
        readonly=True,
    )
    amount = fields.Monetary(string="Amount")
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="receipt_id.currency_id",
        readonly=True,
    )
