# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.disbursement_finance_kmitl.models.disbursement_request import (
    ACCOUNTING_MAKER_GROUP,
)


class DisbursementRequest(models.Model):
    """The ยืนยันล้างหนี้ act: the accounting officer confirms that every payment of
    the request is booked, which is what clears the bills it paid. It posts
    nothing itself: each voucher's entry is posted through the account.move
    maker-checker."""

    _inherit = "disbursement.request"

    clear_confirmer_id = fields.Many2one(
        "res.users", string="Clearing Confirmed By", copy=False, readonly=True
    )
    clear_confirm_date = fields.Datetime(
        string="Clearing Confirmed On", copy=False, readonly=True
    )

    can_confirm_payment_cleared = fields.Boolean(
        compute="_compute_can_confirm_payment_cleared"
    )

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.confirm_cleared",
                "name": _lt("Confirm Cleared"),
                "kind": "act",
                "group": ACCOUNTING_MAKER_GROUP,
                "sequence": 90,
                "module": "disbursement_payment_clear_confirm",
            }
        ]

    @api.depends("state", "payment_ids.state", "clear_confirmer_id")
    @api.depends_context("uid")
    def _compute_can_confirm_payment_cleared(self):
        """Offered once a voucher exists, booked or not: the press says which
        entries are still to post."""
        for rec in self:
            rec.can_confirm_payment_cleared = (
                not rec.clear_confirmer_id
                and any(payment.state != "cancel" for payment in rec.payment_ids)
                and rec._disbursement_act_offered("disbursement.confirm_cleared")
            )

    def _check_payments_booked(self):
        """Raise unless the request's payment is settled and every live voucher's
        entry is posted."""
        self.ensure_one()
        if self.settlement_stage == "booked":
            return
        active = self.payment_ids.filtered(lambda p: p.state != "cancel")
        if not active:
            raise UserError(_("Raise the payment vouchers first."))
        unposted = active.filtered(lambda p: p.state != "posted")
        if unposted:
            raise UserError(
                _("These payment entries are not posted yet: %s")
                % ", ".join(unposted.mapped("display_name"))
            )
        raise UserError(_("Every payee must be paid before the clearing is confirmed."))

    def action_confirm_payment_cleared(self):
        """The act: confirm every payment is booked. It changes no state."""
        for rec in self:
            rec._disbursement_check_act("disbursement.confirm_cleared")
            rec._check_payments_booked()
            # Sudo: the accounting office only reads the request; the act's own
            # check above is what entitles the stamp.
            rec.sudo().write(
                {
                    "clear_confirmer_id": self.env.user.id,
                    "clear_confirm_date": fields.Datetime.now(),
                }
            )
            rec._stamp_signature("payment_clear")
            rec._disbursement_act_done("disbursement.confirm_cleared")
        return True

    def _clear_clearing_confirmation(self):
        """Sudo: a walk-back is often caused by someone who only reads the
        request (the accounting office resetting a voucher's entry)."""
        self.sudo().filtered("clear_confirmer_id").write(
            {"clear_confirmer_id": False, "clear_confirm_date": False}
        )

    def action_draft(self):
        res = super().action_draft()
        self._clear_clearing_confirmation()
        return res

    def _on_settlement_walked_back(self, previous_stage):
        """A payment entry is no longer posted (reset or cancelled), or a payee is
        no longer paid: the confirmation no longer holds."""
        super()._on_settlement_walked_back(previous_stage)
        if self.settlement_stage != "booked" and self.clear_confirmer_id:
            self._archive_signatures(["payment_clear"])
            self._clear_clearing_confirmation()
