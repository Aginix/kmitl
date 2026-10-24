# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    # A bridge-owned Many2one set at create, not a generic reference — see
    # disbursement ADR-0004.
    purchase_guarantee_id = fields.Many2one(
        comodel_name="purchase.guarantee",
        string="Purchase Guarantee",
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        ondelete="set null",
    )

    def _get_source_document(self):
        return self.purchase_guarantee_id or super()._get_source_document()

    @api.depends("purchase_guarantee_id")
    def _compute_is_non_budget(self):
        """Returning a deposit spends none of the institute's money.

        The money has been sitting on a deposit liability since the guarantee
        was receipted; paying it back settles that liability and cuts no
        appropriation — see ADR-0001 and disbursement_budget's ADR-0001.
        """
        super()._compute_is_non_budget()
        for rec in self.filtered("purchase_guarantee_id"):
            rec.is_non_budget = True
