from odoo import _, models

# Approval request states that no longer hold the project open.
APPROVAL_REQUEST_CLOSED_STATES = ("billed", "rejected")


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def _get_open_downstream_documents(self):
        """An approval request still drawing the project's reservation keeps it
        from being closed or deleted (kmitl_project ADR-0011)."""
        res = super()._get_open_downstream_documents()
        count = (
            self.env["approval.request"]
            .sudo()
            .search_count(
                [
                    "|",
                    ("budget_commitment_id.kmitl_project_id", "=", self.id),
                    # A draft that picked the slip but has not drawn it yet.
                    ("reservation_commitment_id.kmitl_project_id", "=", self.id),
                    ("state", "not in", APPROVAL_REQUEST_CLOSED_STATES),
                ]
            )
        )
        if count:
            res.append(_("ใบขออนุมัติที่ยังไม่เสร็จสิ้น %s รายการ") % count)
        return res
