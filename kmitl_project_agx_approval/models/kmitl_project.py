from odoo import _, models

# Approval request states that no longer hold the project open.
APPROVAL_REQUEST_CLOSED_STATES = ("done", "rejected")


class KmitlProject(models.Model):
    _inherit = "kmitl.project"

    def _open_approval_requests(self):
        return (
            self.env["approval.request"]
            .sudo()
            .search(
                [
                    "|",
                    ("budget_commitment_id.kmitl_project_id", "=", self.id),
                    # A draft that picked the slip but has not drawn it yet.
                    ("reservation_commitment_id.kmitl_project_id", "=", self.id),
                    ("state", "not in", APPROVAL_REQUEST_CLOSED_STATES),
                ]
            )
        )

    def _get_open_downstream_documents(self):
        """An approval request still drawing the project's reservation keeps it
        from being closed or deleted (kmitl_project ADR-0011)."""
        res = super()._get_open_downstream_documents()
        count = len(self._open_approval_requests())
        if count:
            res.append(_("ใบขออนุมัติที่ยังไม่เสร็จสิ้น %s รายการ") % count)
        return res

    def _get_project_claims(self):
        """What the open approval requests count on drawing from the project."""
        res = super()._get_project_claims()
        res.append(
            (
                _("ใบขออนุมัติ"),
                sum(self._open_approval_requests().mapped("total_amount")),
            )
        )
        return res
