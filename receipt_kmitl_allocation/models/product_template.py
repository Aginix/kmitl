# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    receipt_allocation_line_ids = fields.One2many(
        "receipt.allocation.line",
        "product_tmpl_id",
        string="Revenue Allocation (Receipt)",
    )
    receipt_allocation_percent_total = fields.Float(
        string="Allocated %",
        compute="_compute_receipt_allocation_percent_total",
    )

    @api.depends(
        "receipt_allocation_line_ids.method",
        "receipt_allocation_line_ids.percentage",
    )
    def _compute_receipt_allocation_percent_total(self):
        for product in self:
            percent_buckets = product.receipt_allocation_line_ids.filtered(
                lambda b: b.method == "percent"
            )
            product.receipt_allocation_percent_total = sum(
                percent_buckets.mapped("percentage")
            )
