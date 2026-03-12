from odoo import _, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    _inherit = "disbursement.request"

    guarantee_id = fields.Many2one(
        comodel_name="purchase.guarantee",
        string="Purchase Guarantee",
        ondelete="set null",
        index=True,
        tracking=True,
    )

    def _create_bill(self):
        bill = super()._create_bill()
        if self.guarantee_id:
            self.guarantee_id.write({"bill_ids": [(4, bill.id)]})
        return bill

    def action_view_purchase_guarantee(self):
        self.ensure_one()
        if not self.guarantee_id:
            raise UserError(_("No Purchase Guarantee linked to this request."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Guarantee"),
            "res_model": "purchase.guarantee",
            "res_id": self.guarantee_id.id,
            "view_mode": "form",
            "target": "current",
        }
