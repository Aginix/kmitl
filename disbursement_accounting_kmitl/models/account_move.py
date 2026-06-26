# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    disbursement_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Disbursement Request",
        ondelete="set null",
        index=True,
        copy=False,
    )
    disbursement_request_name = fields.Char(
        related="disbursement_request_id.name",
        string="Disbursement Request Number",
    )

    def action_view_disbursement_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Disbursement Request"),
            "res_model": "disbursement.request",
            "res_id": self.disbursement_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _post(self, soft=True):
        """Advance the linked disbursement request to ``bills_posted`` once all
        of its active bills are posted.

        Bills no longer post directly from the request — they go through the
        account.move approval (Approve = post). This reacts to that posting,
        regardless of how it was triggered.
        """
        res = super()._post(soft=soft)
        requests = self.mapped("disbursement_request_id").filtered(
            lambda d: d.state == "approved"
        )
        for request in requests:
            active_bills = request.bill_ids.filtered(
                lambda b: b.state != "cancel"
            )
            if active_bills and all(
                b.state == "posted" for b in active_bills
            ):
                request.state = "bills_posted"
        return res


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def action_open_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Vendor Bill"),
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }
