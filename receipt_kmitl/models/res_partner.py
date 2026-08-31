# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError

RECEIPT_EXCLUDED_STATES = ("draft", "cancelled")


class ResPartner(models.Model):
    _inherit = "res.partner"

    receipt_kmitl_count = fields.Integer(compute="_compute_receipt_kmitl_stats")
    receipt_kmitl_total = fields.Monetary(
        compute="_compute_receipt_kmitl_stats",
        currency_field="currency_id",
    )

    def _compute_receipt_kmitl_stats(self):
        receipt_data = self.env["kmitl.receipt"]._read_group(
            [
                ("partner_id", "in", self.ids),
                ("state", "not in", RECEIPT_EXCLUDED_STATES),
            ],
            ["partner_id", "amount_total:sum"],
            ["partner_id"],
        )
        stats = {
            data["partner_id"][0]: data
            for data in receipt_data
        }
        for partner in self:
            data = stats.get(partner.id)
            partner.receipt_kmitl_count = data["partner_id_count"] if data else 0
            partner.receipt_kmitl_total = data["amount_total"] if data else 0

    def action_view_receipt_kmitl(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Receipts"),
            "res_model": "kmitl.receipt",
            "view_mode": "tree,form",
            "views": [(False, "tree"), (False, "form")],
            "domain": [
                ("partner_id", "=", self.id),
                ("state", "not in", RECEIPT_EXCLUDED_STATES),
            ],
        }

    def unlink(self):
        walkin_id = self.env["kmitl.receipt"]._default_partner_id()
        if walkin_id and walkin_id in self.ids:
            raise UserError(
                _("Cannot delete the walk-in customer because it is in use by the receipt system.")
            )
        return super().unlink()
