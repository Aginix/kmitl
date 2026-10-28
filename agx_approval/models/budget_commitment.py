from odoo import _, models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    def _get_open_downstream_documents(self):
        """An approval request not yet closed, reserving on or drawing down
        this reservation, blocks กลับแบบร่าง and ลบใบจอง."""
        documents = super()._get_open_downstream_documents()
        requests = (
            self.env["approval.request"]
            .sudo()
            .search(
                [
                    "|",
                    ("budget_commitment_id", "=", self.id),
                    ("reservation_commitment_id", "=", self.id),
                    ("state", "not in", ("billed", "rejected")),
                ]
            )
        )
        return documents + [_("ใบขออนุมัติ %s") % r.display_name for r in requests]
