# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    is_disbursed = fields.Boolean(
        string="Disbursed",
        default=False,
        copy=False,
        tracking=True,
    )

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    @api.constrains("state")
    def _check_pending_disbursement_before_accept(self):
        """ห้าม accept WA ใหม่ถ้า PO ยังมี WA ที่ยังไม่ถูก submit disbursement"""
        for wa in self:
            if wa.state != "accept" or not wa.purchase_id:
                continue
            blocking = self.search([
                ("purchase_id", "=", wa.purchase_id.id),
                ("state", "=", "accept"),
                ("is_disbursed", "=", False),
                ("id", "!=", wa.id),
            ])
            if blocking:
                raise UserError(
                    _(
                        "Cannot accept this Work Acceptance.\n"
                        "PO '%s' still has WA '%s' waiting for disbursement submission."
                    ) % (wa.purchase_id.name, blocking[0].name)
                )
            
class WorkAcceptanceLine(models.Model):
    _inherit = "work.acceptance.line"

    def _prepare_disbursement_line_vals(self):
        """Convert WA line to disbursement request line vals."""
        # ดึง account จาก product เหมือน PO line
        account = (
            self.product_id.property_account_expense_id
            or self.product_id.categ_id.property_account_expense_categ_id
        )
        # ดึง analytic จาก PO line ที่ link อยู่ (ถ้ามี)
        analytic = (
            self.purchase_line_id.analytic_distribution
            if self.purchase_line_id
            else False
        )
        # ดึง taxes จาก PO line ที่ link อยู่ (ถ้ามี)
        tax_ids = (
            self.purchase_line_id.taxes_id.ids
            if self.purchase_line_id
            else []
        )
        return {
            "product_id": self.product_id.id,
            "name": self.name,
            "quantity": self.product_qty,
            "price_unit": self.price_unit,
            "account_id": account.id if account else False,
            "tax_ids": [(6, 0, tax_ids)],
            "analytic_distribution": analytic,
        }
