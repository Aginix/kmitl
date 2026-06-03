from odoo import _, models

PR_STATUS_FYI = "kmitl_todo.mail_activity_pr_status_fyi"


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    def _notify_requester_fyi(self, status_label):
        """UC3 — FYI to the requester (ผู้ขอ) when the พ.1 changes status.

        Routed to ``requested_by`` (a single user); cleared by Mark as Read or
        the retention cron (ADR-0003). ``button_approved``/``button_rejected``
        are called by both the manual and the Sarabun-auto paths, so this fires
        in every case.
        """
        if not self.env.ref(PR_STATUS_FYI, raise_if_not_found=False):
            return
        for rec in self:
            if rec.requested_by:
                rec.activity_schedule(
                    PR_STATUS_FYI,
                    summary=_("พ.1 %(name)s %(status)s")
                    % {"name": rec.display_name, "status": status_label},
                    user_id=rec.requested_by.id,
                )

    def button_approved(self):
        res = super().button_approved()
        self._notify_requester_fyi(_("ได้รับการอนุมัติแล้ว"))
        return res

    def button_rejected(self):
        res = super().button_rejected()
        self._notify_requester_fyi(_("ถูกตีกลับ"))
        return res
