from odoo import fields, models


class BudgetTransfer(models.Model):
    _inherit = "budget.transfer"

    support_request_id = fields.Many2one(
        comodel_name="budget.support.request",
        string="Support Request",
        ondelete="set null",
        copy=False,
    )

    def action_submit(self):
        """A transfer fulfilling an approved support request posts on ยืนยัน:
        the request's own approval is the authority, so it needs neither a
        second หนังสือ nor a second approver (CONTEXT.md ▸ Fulfil).

        Filtered on the state *after* super — a confirm hook (e.g. the
        exception popup) may return without submitting."""
        res = super().action_submit()
        funded = self.filtered(
            lambda t: (
                t.state == "submitted"
                and t.support_request_id.state in ("approved", "in_progress")
            )
        )
        for transfer in funded:
            transfer.support_request_id._check_can_fulfil()
        if funded:
            funded.write(
                {
                    "approver_id": self.env.user.id,
                    "approval_date": fields.Datetime.now(),
                }
            )
            funded._post_transfer()
        return res

    def _post_transfer(self):
        res = super()._post_transfer()
        self.mapped("support_request_id")._on_fulfilment_posted()
        return res
