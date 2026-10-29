# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError

ACCOUNTING_GROUP = "accounting_kmitl.group_accounting_kmitl_user"


class DisbursementRequest(models.Model):
    """The ตั้งหนี้ act: the accounting officer confirms that every bill of the
    request is posted, so the request leaves the billing station ready for the
    payment audit."""

    _inherit = "disbursement.request"

    bill_confirmer_id = fields.Many2one(
        "res.users", string="Bills Confirmed By", copy=False, readonly=True
    )
    bill_confirm_date = fields.Datetime(
        string="Bills Confirmed On", copy=False, readonly=True
    )

    can_confirm_bill = fields.Boolean(compute="_compute_can_confirm_bill")

    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.confirm_bill",
                "name": _lt("Confirm Bills Posted"),
                "kind": "act",
                "group": ACCOUNTING_GROUP,
                "sequence": 55,
                "module": "disbursement_bill_posted_confirm",
            }
        ]

    @api.depends("state", "bill_ids.state", "bill_confirmer_id")
    @api.depends_context("uid")
    def _compute_can_confirm_bill(self):
        """Offered once a bill exists, posted or not: the press says which bills
        are still to post."""
        for rec in self:
            rec.can_confirm_bill = (
                not rec.bill_confirmer_id
                and any(bill.state != "cancel" for bill in rec.bill_ids)
                and rec._disbursement_act_offered("disbursement.confirm_bill")
            )

    def _check_bills_posted(self):
        """Raise unless the request has bills and every live one is posted."""
        self.ensure_one()
        active = self.bill_ids.filtered(lambda b: b.state != "cancel")
        if not active:
            raise UserError(_("Create the bills first."))
        unposted = active.filtered(lambda b: b.state != "posted")
        if unposted:
            raise UserError(
                _("These bills are not posted yet: %s")
                % ", ".join(unposted.mapped("display_name"))
            )

    def action_confirm_bill(self):
        """The act: confirm the bills are posted. It changes no state."""
        for rec in self:
            rec._disbursement_check_act("disbursement.confirm_bill")
            rec._check_bills_posted()
            rec.bill_confirmer_id = self.env.user
            rec.bill_confirm_date = fields.Datetime.now()
            rec._stamp_signature("bill_confirm")
            rec._disbursement_act_done("disbursement.confirm_bill")
        return True

    def _clear_bill_confirmation(self):
        self.filtered("bill_confirmer_id").write(
            {"bill_confirmer_id": False, "bill_confirm_date": False}
        )

    def action_draft(self):
        res = super().action_draft()
        self._clear_bill_confirmation()
        return res

    def _on_settlement_walked_back(self, previous_stage):
        """A posted bill reset or cancelled: the confirmation no longer holds."""
        super()._on_settlement_walked_back(previous_stage)
        if self.settlement_stage == "none" and self.bill_confirmer_id:
            self._archive_signatures(["bill_confirm"])
            self._clear_bill_confirmation()
