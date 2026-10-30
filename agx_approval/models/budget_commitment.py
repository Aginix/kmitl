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
                    ("state", "not in", ("done", "rejected")),
                ]
            )
        )
        return documents + [_("ใบขออนุมัติ %s") % r.display_name for r in requests]

    def get_reservation_info(self):
        """Whoever may read an approval request sees the card of its
        reservation on it, even from another unit (e.g. a ใบขอเบิก reviewer,
        agx_approval ADR-0010) — the card only, not the reservation itself."""
        requests = self.env["approval.request"].search(
            [("budget_commitment_id", "in", self.ids)]
        )
        if self and self <= requests.sudo().budget_commitment_id:
            return super(BudgetCommitment, self.sudo()).get_reservation_info()
        return super().get_reservation_info()
