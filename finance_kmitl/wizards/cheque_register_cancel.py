# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models

from odoo.addons.finance_kmitl.models.cheque_register import CANCEL_REASONS


class ChequeRegisterCancel(models.TransientModel):
    """Ask why a cheque died, and whether another one takes its place.

    Both answers are only known at this moment and neither can be derived: the
    reason is what the officer just found out, and whether to write a replacement
    depends on whether the payee is still owed — which is usually yes, and
    occasionally no, because the whole disbursement is being unwound instead.
    """

    _name = "cheque.register.cancel"
    _description = "Cancel Cheque"

    cheque_id = fields.Many2one(
        comodel_name="cheque.register",
        string="Cheque",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    # Held here and not as a writable related on the cheque: a related would put
    # the reason on the record the moment it is picked, so a cancellation the
    # officer thought better of would leave a live cheque carrying a reason for
    # its own death.
    reason = fields.Selection(
        selection=CANCEL_REASONS,
        string="Reason",
        required=True,
    )
    replace = fields.Boolean(
        string="Write a Replacement Cheque",
        default=True,
        help="Keep the same payment voucher and start another cheque for it, "
        "numbered next in the book. Leave this off only when the payee is no "
        "longer to be paid at all.",
    )
    was_handed_over = fields.Boolean(
        compute="_compute_was_handed_over",
        help="Drives the warning: cancelling a cheque the payee already took "
        "withdraws the claim that they were paid.",
    )

    @api.depends("cheque_id.state")
    def _compute_was_handed_over(self):
        for wizard in self:
            wizard.was_handed_over = wizard.cheque_id.state == "paid"

    def action_cancel_cheque(self):
        self.ensure_one()
        replacements = self.cheque_id._cancel(self.reason, replace=self.replace)
        if not replacements:
            return {"type": "ir.actions.act_window_close"}
        return {
            "type": "ir.actions.act_window",
            "name": _("Replacement Cheque"),
            "res_model": "cheque.register",
            "res_id": replacements[0].id,
            "view_mode": "form",
            "target": "current",
        }
