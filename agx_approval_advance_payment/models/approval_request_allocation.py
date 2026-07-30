from odoo import fields, models


class ApprovalRequestAllocation(models.Model):
    _inherit = "approval.request.allocation"

    # Seam for the advance_payment overhaul (ADR-0002, scope 2): links an
    # `advance` (เงินยืม) row to the borrower's สัญญายืม so the overhaul can write
    # the usage clearing against it. Nullable and unwired in scope 1 — clearing
    # is deferred, so this only reserves the link for later.
    advance_payment_id = fields.Many2one(
        comodel_name="advance.payment",
        string="สัญญายืมเงิน",
        copy=False,
        help="สัญญายืมที่แถวเงินยืมนี้จะไปเคลียร์ (ใช้เมื่อประเภทการจ่ายเงิน = เงินยืม)",
    )
