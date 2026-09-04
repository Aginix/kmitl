# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models


class ReceiptRemittance(models.Model):
    _inherit = "kmitl.receipt.remittance"

    def action_view_summary_report(self):
        """Open the Receipt Summary Report scoped to this remittance's
        receipts only."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "receipt_kmitl_summary_report",
            "name": _("Receipt Summary: %s") % (self.name or ""),
            "target": "current",
            "params": {
                "remittance_id": self.id,
                "remittance_name": self.name,
                "company_id": self.company_id.id,
            },
        }
