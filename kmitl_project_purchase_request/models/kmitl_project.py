from odoo import _, models

# Purchase request states that no longer hold the project open.
PURCHASE_REQUEST_CLOSED_STATES = ("done", "rejected", "cancelled")


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def _get_open_downstream_documents(self):
        """A purchase request still open on the project keeps it from being
        closed or deleted (kmitl_project ADR-0011)."""
        res = super()._get_open_downstream_documents()
        count = (
            self.env["purchase.request"]
            .sudo()
            .search_count(
                [
                    ("kmitl_project_id", "=", self.id),
                    ("state", "not in", PURCHASE_REQUEST_CLOSED_STATES),
                ]
            )
        )
        if count:
            res.append(_("ใบขอซื้อขอจ้าง (พ.1) ที่ยังไม่เสร็จสิ้น %s รายการ") % count)
        return res

    def _get_project_claims(self):
        """The พ.1 total its cap holds within ``budget_amount`` (ADR-0007)."""
        res = super()._get_project_claims()
        res.append((_("ใบขอซื้อขอจ้าง (พ.1)"), self.sudo()._project_pr_total()))
        return res
