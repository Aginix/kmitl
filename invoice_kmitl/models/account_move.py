# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    kmitl_invoice_id = fields.Many2one(
        "kmitl.invoice",
        string="KMITL Invoice",
        readonly=True,
        copy=False,
        index=True,
        help="The invoice this entry raises, settles or reverses.",
    )

    def _check_submit_allowed(self):
        """An entry raised for a KMITL invoice may be submitted by any accounting maker.

        The creator rule guards an entry an accounting person typed. These are raised
        by the treasury office, so they have no accounting author: without this the
        accounting office could not submit them at all. Same reasoning as the payment
        vouchers handed over by ``finance_kmitl``.
        """
        others = self.filtered(lambda move: not move.kmitl_invoice_id)
        if others:
            super(AccountMove, others)._check_submit_allowed()
        return True

    # The dependencies of a compute add up over its overrides, so only the new one
    # is declared here.
    @api.depends("kmitl_invoice_id")
    def _compute_can_submit(self):
        super()._compute_can_submit()
        for move in self.filtered("kmitl_invoice_id"):
            move.can_submit = True

    def _post(self, soft=True):
        # After super() and on what it returns: a move dated in the future is left
        # unposted, and an unposted move cannot be reconciled.
        posted = super()._post(soft=soft)
        posted.filtered("kmitl_invoice_id").kmitl_invoice_id.sudo()._auto_reconcile()
        return posted
