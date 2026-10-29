# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.disbursement_finance_kmitl.models.disbursement_request import (
    FINANCE_GROUP,
)


class DisbursementRequest(models.Model):
    """The ยืนยันจ่ายสำเร็จ act: the finance officer confirms that every payee of
    the request has been paid. It pays nothing itself: each voucher is paid by
    the e-payment file, the cheque or the cash press that carried it."""

    _inherit = "disbursement.request"

    paid_confirmer_id = fields.Many2one(
        "res.users", string="Payment Confirmed By", copy=False, readonly=True
    )
    paid_confirm_date = fields.Datetime(
        string="Payment Confirmed On", copy=False, readonly=True
    )

    can_confirm_payment_paid = fields.Boolean(
        compute="_compute_can_confirm_payment_paid"
    )

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.confirm_paid",
                "name": _lt("Confirm Payment Completed"),
                "kind": "act",
                "group": FINANCE_GROUP,
                "sequence": 80,
                "module": "disbursement_payment_paid_confirm",
            }
        ]

    @api.depends("state", "payment_ids.state", "paid_confirmer_id")
    @api.depends_context("uid")
    def _compute_can_confirm_payment_paid(self):
        """Offered once a voucher exists, paid or not: the press says which
        payees are still to be paid."""
        for rec in self:
            rec.can_confirm_payment_paid = (
                not rec.paid_confirmer_id
                and any(payment.state != "cancel" for payment in rec.payment_ids)
                and rec._disbursement_act_offered("disbursement.confirm_paid")
            )

    def _check_payees_paid(self):
        """Raise unless every payee has a live voucher and every live voucher is
        paid."""
        self.ensure_one()
        active = self.payment_ids.filtered(lambda p: p.state != "cancel")
        if not active:
            raise UserError(_("Raise the payment vouchers first."))
        unpaid = active.filtered(lambda p: p.finance_state != "paid")
        if unpaid:
            raise UserError(
                _("These vouchers are not paid yet: %s")
                % ", ".join(unpaid.mapped("display_name"))
            )
        missing = self._payable_payment_lines()
        if missing:
            raise UserError(
                _("These payees have no voucher yet: %s")
                % ", ".join(missing.mapped("partner_id.display_name"))
            )

    def action_confirm_payment_paid(self):
        """The act: confirm every payee is paid. It changes no state."""
        for rec in self:
            rec._disbursement_check_act("disbursement.confirm_paid")
            rec._check_payees_paid()
            rec.write(
                {
                    "paid_confirmer_id": self.env.user.id,
                    "paid_confirm_date": fields.Datetime.now(),
                }
            )
            rec._stamp_signature("payment_paid")
            rec._disbursement_act_done("disbursement.confirm_paid")
        return True

    def _clear_paid_confirmation(self):
        """Sudo: a walk-back is often caused by someone who only reads the
        request (the accounting office resetting a voucher's entry)."""
        self.sudo().filtered("paid_confirmer_id").write(
            {"paid_confirmer_id": False, "paid_confirm_date": False}
        )

    def action_draft(self):
        res = super().action_draft()
        self._clear_paid_confirmation()
        return res

    def _on_settlement_walked_back(self, previous_stage):
        """A voucher is no longer paid (a cheque bounced, a voucher cancelled or
        removed): the confirmation no longer holds."""
        super()._on_settlement_walked_back(previous_stage)
        if (
            self.settlement_stage not in ("settled", "booked")
            and self.paid_confirmer_id
        ):
            self._archive_signatures(["payment_paid"])
            self._clear_paid_confirmation()
