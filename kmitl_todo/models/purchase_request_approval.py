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
        act_type = self.env.ref(PR_STATUS_FYI, raise_if_not_found=False)
        if not act_type:
            return
        for rec in self:
            if not rec.requested_by:
                continue
            # Supersede: keep only the latest status FYI per requester. Use
            # unlink (not activity_feedback) so the superseded FYI does not land
            # in the Completed history as a phantom completion.
            rec.activity_ids.filtered(
                lambda a: a.activity_type_id == act_type
                and a.user_id.id == rec.requested_by.id
            ).unlink()
            rec.activity_schedule(
                PR_STATUS_FYI,
                summary=_("Purchase request %(name)s %(status)s")
                % {"name": rec.display_name, "status": status_label},
                user_id=rec.requested_by.id,
            )

    def button_approved(self):
        res = super().button_approved()
        self._notify_requester_fyi(_("approved"))
        return res

    def button_rejected(self):
        res = super().button_rejected()
        self._notify_requester_fyi(_("rejected"))
        return res
