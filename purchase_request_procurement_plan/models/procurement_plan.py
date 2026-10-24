from odoo import _, models

# Purchase request states that no longer hold the plan open.
PURCHASE_REQUEST_CLOSED_STATES = ("done", "rejected", "cancelled")


class ProcurementPlan(models.Model):
    _inherit = "procurement.plan"

    def _get_open_downstream_documents(self):
        """A purchase request still open on the plan keeps it from being closed
        or deleted (procurement_plan ADR-0005)."""
        res = super()._get_open_downstream_documents()
        count = (
            self.env["purchase.request"]
            .sudo()
            .search_count(
                [
                    ("procurement_plan_id", "=", self.id),
                    ("state", "not in", PURCHASE_REQUEST_CLOSED_STATES),
                ]
            )
        )
        if count:
            res.append(_("ใบขอซื้อขอจ้าง (พ.1) ที่ยังไม่เสร็จสิ้น %s รายการ") % count)
        return res

    def _get_plan_claims(self):
        """The total of the plan's live purchase requests: a Floating Return
        must leave that much behind."""
        res = super()._get_plan_claims()
        requests = (
            self.env["purchase.request"]
            .sudo()
            .search(
                [
                    ("procurement_plan_id", "=", self.id),
                    ("state", "not in", ("rejected", "cancelled")),
                ]
            )
        )
        res.append((_("ใบขอซื้อขอจ้าง (พ.1)"), sum(requests.mapped("estimated_cost"))))
        return res
