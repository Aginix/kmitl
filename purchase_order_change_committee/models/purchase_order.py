from odoo import models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_view_wa(self):
        result = super().action_view_wa()
        committees = self.work_acceptance_committee_ids
        lines = [
            (0, 0, self._prepare_committee_line(line)) for line in committees
        ]
        result["context"]["default_work_acceptance_committee_ids"] = lines
        return result
