# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models


class AccountMove(models.Model):
    """Links a handover entry back to the disbursement request it funds.

    Deliberately its own field rather than the existing
    ``disbursement_request_id``: that one is the inverse of the request's
    ``bill_ids``, which carries no ``move_type`` filter, so a handover reusing it
    would *be* one of the request's vendor bills — blocking bill creation, and
    advancing the request to ``bills_posted`` the moment the handover posted.
    """

    _inherit = "account.move"

    cash_revenue_handover_request_id = fields.Many2one(
        comodel_name="disbursement.request",
        string="Handover For",
        ondelete="set null",
        index=True,
        copy=False,
        readonly=True,
        help="The disbursement request this handover entry funds.",
    )
    cash_revenue_handover_request_name = fields.Char(
        related="cash_revenue_handover_request_id.name",
        string="Handover For Number",
    )

    def action_view_handover_request(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Disbursement Request"),
            "res_model": "disbursement.request",
            "res_id": self.cash_revenue_handover_request_id.id,
            "view_mode": "form",
            "target": "current",
        }
