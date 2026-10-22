# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.disbursement.models.disbursement_request import (
    DisbursementRequest as DisbursementRequestBase,
)


class DisbursementRequest(models.Model):
    """ตั้งเบิกตรง (disbursement ADR-0005).

    A direct claim is raised on a memo produced outside the system, which
    already carries the head of department's signature: its number, date and
    scan are recorded on the request, and submit goes straight to ``signed``
    — so it never waits at ``submitted`` for e-Saraban. Budget-wise it may
    still draw a reservation; ``disbursement_direct_claim_budget`` consumes
    it directly from the pool when it does not.
    """

    _inherit = "disbursement.request"

    # Independent of ``payment_type``: จ่ายตรง is how the payee is paid.
    is_direct_claim = fields.Boolean(
        string="Direct Claim",
        tracking=True,
        copy=False,
        states=DisbursementRequestBase.READONLY_STATES,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # After super(): the flag may also come from a default_ context key.
        if records.filtered("is_direct_claim"):
            self._check_direct_claim_right()
        return records

    def write(self, vals):
        if "is_direct_claim" in vals and self.filtered(
            lambda r: r.is_direct_claim != bool(vals["is_direct_claim"])
        ):
            self._check_direct_claim_right()
        return super().write(vals)

    def _check_direct_claim_right(self):
        """Only users granted ตั้งเบิกตรง may tick or untick it."""
        if not self.env.su and not self.env.user.has_group(
            "disbursement_direct_claim.group_disbursement_direct_claim"
        ):
            raise AccessError(
                _("Only users with the Direct Claim right may set or clear it.")
            )

    def action_submit(self):
        for record in self.filtered(lambda r: r.is_direct_claim and r.state == "draft"):
            record._check_direct_claim_memo()
        res = super().action_submit()
        # The external memo already carries the head's signature.
        self.filtered(
            lambda r: r.is_direct_claim and r.state == "submitted"
        ).action_sign()
        return res

    def _check_direct_claim_memo(self):
        self.ensure_one()
        if not self.memo_number:
            raise UserError(_("A direct claim needs the memo number."))
        if not self.sign_date:
            raise UserError(_("A direct claim needs the date the memo was signed."))
        if not self.attachment_ids:
            raise UserError(_("A direct claim needs the memo attached to the request."))

    def action_draft(self):
        # The memo's own date survives a reset; core clears the stamped one.
        typed = {r: r.sign_date for r in self if r.is_direct_claim}
        res = super().action_draft()
        for record, sign_date in typed.items():
            record.sign_date = sign_date
        return res
