from odoo import _, fields, models
from odoo.exceptions import UserError

# Config parameters set by finance in Settings (advance.payment settings page).
PARAM_PRODUCT = "advance_payment_receipt_kmitl.return_product_id"
PARAM_METHOD = "advance_payment_receipt_kmitl.return_payment_method_id"


class AdvancePaymentReturnLine(models.Model):
    """Settle a returned advance by issuing a KMITL cash receipt instead of the
    base module's draft inbound ``account.payment``.

    The receipt is the single money-in + accounting document (it posts its own
    ``account.move`` through the remittance workflow), so no ``account.payment``
    is created here — that avoids booking the same money twice.
    """

    _inherit = "advance.payment.return.line"

    receipt_id = fields.Many2one(
        comodel_name="kmitl.receipt",
        string="Receipt",
        readonly=True,
        copy=False,
    )

    # -- officer-entered receiving details (filled in pending_review) -------- #

    receipt_payment_method_id = fields.Many2one(
        comodel_name="kmitl.payment.method",
        string="โอนเข้าบัญชี",
        domain=[("payment_type", "=", "transfer")],
        default=lambda self: self._default_receipt_payment_method_id(),
        readonly=True,
        states={"pending_review": [("readonly", False)]},
        copy=False,
        help="บัญชีธนาคารที่รับเงินคืน ใช้เป็นวิธีรับเงินและบัญชีเดบิตบนใบเสร็จ",
    )
    receipt_transfer_date = fields.Date(
        string="วันที่โอนเงิน",
        default=fields.Date.context_today,
        readonly=True,
        states={"pending_review": [("readonly", False)]},
        copy=False,
    )

    def _default_receipt_payment_method_id(self):
        method_id = self.env["ir.config_parameter"].sudo().get_param(PARAM_METHOD)
        return int(method_id) if method_id else False

    def action_view_receipt(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.receipt",
            "res_id": self.receipt_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    # -- settlement seam overrides (advance_payment) ------------------------- #

    def _settle_return(self):
        """Issue a ``kmitl.receipt`` (draft) for the returned money and link it.

        Overrides the base, which would create a draft ``account.payment``.
        """
        self.ensure_one()
        # create is ACL-gated to receipt users; the อนุมัติ button is already
        # gated to the loan officer, so sudo() the create the same way the base
        # settlement does for account.payment.
        receipt = (
            self.env["kmitl.receipt"]
            .sudo()
            .create(self._prepare_return_receipt_vals())
        )
        receipt._sync_customer_snapshot()
        self.receipt_id = receipt.id
        return _(
            "Receipt"
            " <a href='/web#id=%(rid)s&amp;model=kmitl.receipt'>"
            "<b>%(rname)s</b></a> issued.",
            rid=receipt.id,
            rname=receipt.name,
        )

    def _cancel_return_settlement(self):
        """Undo the issued receipt on admin reset.

        A receipt that has already entered the remittance/posting workflow
        carries GL and a remittance link, so it cannot be silently voided here.
        """
        self.ensure_one()
        if not self.receipt_id:
            return super()._cancel_return_settlement()
        receipt = self.receipt_id
        if receipt.state != "draft":
            raise UserError(
                _(
                    "Cannot reset: receipt %s is already in the remittance/"
                    "posting workflow. Handle it from Receipts first."
                )
                % receipt.name
            )
        receipt.sudo().action_cancel()
        self.receipt_id = False

    # -- receipt vals -------------------------------------------------------- #

    def _prepare_return_receipt_vals(self):
        """Build a valid ``kmitl.receipt`` (with one line) for this return.

        All of the receipt's create-time constraints (a line with an income
        account, a positive total, a payment method matching the payment type,
        a required department dimension) are satisfied in the single dict below.
        """
        self.ensure_one()
        agreement = self.agreement_id
        if not self.receipt_payment_method_id:
            raise UserError(
                _(
                    "Set the receiving payment method (โอนเข้าบัญชี) before "
                    "issuing the receipt."
                )
            )
        if not agreement.department_analytic_id:
            raise UserError(
                _(
                    "Agreement %s has no department (ส่วนงาน) set. The "
                    "receipt requires it — set it on the agreement first."
                )
                % agreement.name
            )
        product = self.env["product.product"].browse(
            int(
                self.env["ir.config_parameter"].sudo().get_param(PARAM_PRODUCT)
                or 0
            )
        )
        if not product.exists():
            raise UserError(
                _(
                    "Set the advance-payment return product in Settings "
                    "before issuing a receipt."
                )
            )
        account = (
            product.property_account_income_id
            or product.categ_id.property_account_income_categ_id
        )
        if not account:
            raise UserError(
                _(
                    "Product '%s' has no income account. Configure one before "
                    "issuing a receipt."
                )
                % product.display_name
            )
        line_description = _("Return of advance payment %s") % (agreement.name or "")
        header_description = _(
            "คืนเงินยืมทดรองจ่าย สัญญาเลขที่ %(agreement)s "
            "ผู้ยืม %(employee)s เหตุผลการยืม %(reason)s"
        ) % {
            "agreement": agreement.name or "-",
            "employee": agreement.employee_id.name or "-",
            "reason": agreement.loan_reason or "-",
        }
        return {
            "date": self.date,
            "partner_id": agreement.partner_id.id,
            "is_walkin": False,
            "payment_type": "transfer",
            "payment_method_id": self.receipt_payment_method_id.id,
            "transfer_date": self.receipt_transfer_date,
            "advance_return_line_id": self.id,
            "description": header_description,
            # department_analytic_id is set explicitly (not left to compute from
            # analytic_distribution alone) since it's a required field on
            # kmitl.receipt; analytic_distribution still carries the rest of the
            # agreement's dimensions (fund/source/activity).
            "department_analytic_id": agreement.department_analytic_id.id,
            "analytic_distribution": agreement.analytic_distribution,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": line_description,
                        "account_id": account.id,
                        "quantity": 1.0,
                        "price_unit": self.amount,
                    },
                )
            ],
        }
