from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    # Kept apart from ``disbursement_request_id``: a clearing entry is not a
    # bill, so it must never count in ``bill_ids``.
    advance_clearing_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Advance Clearing Request",
        ondelete="set null",
        index=True,
        copy=False,
    )

    def button_draft(self):
        """Resetting a clearing entry walks the request's settlement stage back."""
        requests = self.mapped("advance_clearing_request_id")
        before = requests._settlement_snapshot()
        res = super().button_draft()
        requests._settlement_check(before)
        return res

    def button_cancel(self):
        requests = self.mapped("advance_clearing_request_id")
        before = requests._settlement_snapshot()
        res = super().button_cancel()
        requests._settlement_check(before)
        return res
