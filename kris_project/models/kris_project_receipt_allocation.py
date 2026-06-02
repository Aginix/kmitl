from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


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

    @api.constrains("amount", "allocation_line_id")
    def _check_actual_not_exceed_estimated(self):
        prec = self.env["decimal.precision"].precision_get("Account")
        for alloc_line in self.mapped("allocation_line_id"):
            actual = sum(alloc_line.receipt_allocation_ids.mapped("amount"))
            if (
                float_compare(
                    actual, alloc_line.estimated_amount, precision_digits=prec
                )
                > 0
            ):
                raise ValidationError(
                    _(
                        "ยอดจัดสรรจริงของ %s (%.2f บาท) เกินประมาณการ (%.2f บาท)"
                    )
                    % (alloc_line.name or "", actual, alloc_line.estimated_amount)
                )
