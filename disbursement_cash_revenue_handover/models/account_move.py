# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class AccountMove(models.Model):
    """Links a handover entry back to the disbursement request it funds, and
    keeps its header dimensions from flattening its lines.

    The back-link is deliberately its own field rather than the existing
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

    # ------------------------------------------------------------------
    # Header dimensions never reach a handover's lines
    # ------------------------------------------------------------------
    # A handover's header carries the funded request's dimensions so the entry
    # reads as "this funds that request" and the move form's required dimension
    # fields are filled. Its two sides carry deliberately *different* dimensions,
    # though, so the propagation ``accounting_kmitl`` does — header onto every
    # line — has to stop at a handover, or the entry collapses onto one set of
    # dimensions and moves nothing. Only the convenience Many2one fields are kept
    # in step, which is the shared mixin's own half of the inverse.

    def _inverse_analytic_distribution(self):
        handovers = self.filtered("cash_revenue_handover_request_id")
        super(AccountMove, self - handovers)._inverse_analytic_distribution()
        for move in handovers.filtered("analytic_distribution"):
            move._process_analytic_distribution_ids()

    @api.onchange("analytic_distribution")
    def _onchange_analytic_distribution(self):
        if self.cash_revenue_handover_request_id:
            return None
        return super()._onchange_analytic_distribution()
