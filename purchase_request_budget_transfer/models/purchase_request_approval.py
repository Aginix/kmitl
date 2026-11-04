from odoo import fields, models


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    payment_type = fields.Selection(
        selection_add=[("budget_transfer", "Budget Transfer")],
        ondelete={"budget_transfer": "set null"},
    )

    def purchase_request_approval_check_partner_required(self):
        # โอนงบ ไม่มีคู่ค้า เหมือนเงินยืม / สำรองจ่าย.
        return (
            super()
            .purchase_request_approval_check_partner_required()
            .filtered(lambda r: r.payment_type != "budget_transfer")
        )
