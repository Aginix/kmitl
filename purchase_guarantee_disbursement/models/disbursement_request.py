# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    reference = fields.Reference(
        selection_add=[("purchase.guarantee", "Purchase Guarantee")],
        ondelete={"purchase.guarantee": "set null"},
    )

    purchase_guarantee_id = fields.Many2one(
        comodel_name="purchase.guarantee",
        string="Purchase Guarantee",
        compute="_compute_reference_fields",
        store=True,
        index=True,
        tracking=True,
    )

    @api.depends("reference")
    def _compute_reference_fields(self):
        super()._compute_reference_fields()
        for rec in self:
            if rec.reference and rec.reference._name == "purchase.guarantee":
                rec.purchase_guarantee_id = rec.reference
            else:
                rec.purchase_guarantee_id = False

    @api.depends("purchase_guarantee_id")
    def _compute_is_non_budget(self):
        """Returning a deposit spends none of the institute's money.

        The money has been sitting on a deposit liability since the guarantee
        was receipted; paying it back settles that liability and cuts no
        appropriation — see ADR-0001 and disbursement's ADR-0003.
        """
        super()._compute_is_non_budget()
        for rec in self.filtered("purchase_guarantee_id"):
            rec.is_non_budget = True
