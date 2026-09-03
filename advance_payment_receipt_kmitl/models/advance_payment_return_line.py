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
        ICP = self.env["ir.config_parameter"].sudo()
        product = self.env["product.product"].browse(
            int(ICP.get_param(PARAM_PRODUCT) or 0)
        )
        method = self.env["kmitl.payment.method"].browse(
            int(ICP.get_param(PARAM_METHOD) or 0)
        )
        if not product.exists() or not method.exists():
            raise UserError(
                _(
                    "Set the advance-payment return product and payment method "
                    "in Settings before approving a return."
                )
            )
        if method.payment_type == "cheque":
            raise UserError(
                _(
                    "The configured return payment method is a cheque method, "
                    "which returns do not capture. Choose a cash or transfer "
                    "method in Settings."
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
                    "approving a return."
                )
                % product.display_name
            )
        vals = {
            "date": self.date,
            "partner_id": agreement.partner_id.id,
            "is_walkin": False,
            "payment_type": method.payment_type,
            "payment_method_id": method.id,
            # analytic.mixin JSON is the source of truth; copying it carries the
            # agreement's dimensions and populates the receipt's required
            # department_analytic_id.
            "analytic_distribution": agreement.analytic_distribution,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": _("Return of advance payment %s")
                        % (agreement.name or ""),
                        "account_id": account.id,
                        "quantity": 1.0,
                        "price_unit": self.amount,
                    },
                )
            ],
        }
        if method.payment_type == "transfer":
            vals["transfer_date"] = self.date
        return vals
