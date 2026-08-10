from odoo import _, models

PR_STATUS_FYI = "purchase_request_todo.mail_activity_pr_status_fyi"
PA_AWAITING_MANAGER_ACTIVITY = (
    "purchase_request_todo.mail_activity_pa_awaiting_manager"
)
PA_APPROVED_RECORD_CONTRACT_ACTIVITY = (
    "purchase_request_todo.mail_activity_pa_approved_record_contract"
)
PR_ENDORSEMENT_APPROVED_ACTIVITY = (
    "purchase_request_todo.mail_activity_pr_endorsement_approved"
)


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    # ---------------------------------------------------------------------
    # Existing UC3 — FYI to requester (mail_activity_pr_status_fyi)
    # ---------------------------------------------------------------------
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

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _schedule_personal_todo(self, xmlid, user, summary):
        """Personal Todo, deduplicated per (activity type, user)."""
        self.ensure_one()
        act_type = self.env.ref(xmlid, raise_if_not_found=False)
        if not act_type or not user:
            return
        self.activity_ids.filtered(
            lambda a: a.activity_type_id == act_type and a.user_id.id == user.id
        ).unlink()
        self.activity_schedule(xmlid, summary=summary, user_id=user.id)

    # ---------------------------------------------------------------------
    # Awaiting manager consideration (draft → to_approve)
    # ---------------------------------------------------------------------
    def _awaiting_manager_todo_summary(self):
        """From-name shows the พ.1 procurement officer (assigned_to on the PR)
        so the manager knows who sent it — falls back to the PA's own
        ``user_id`` if the PR link or assignment is missing."""
        self.ensure_one()
        pr = self.request_id
        sender = pr.assigned_to if pr else self.env["res.users"]
        if not sender:
            sender = self.user_id
        sender_name = sender.name if sender else _("เจ้าหน้าที่พัสดุ")
        return _(
            "ท่านได้รับ แบบรายงานขอให้จัดซื้อจัดจ้าง (พจ.1) จาก %(sender)s "
            "เพื่อให้ท่านดำเนินการ พิจารณา"
        ) % {"sender": sender_name}

    def _schedule_awaiting_manager_todo(self):
        for rec in self:
            if not rec.assigned_to:
                continue
            rec._schedule_personal_todo(
                PA_AWAITING_MANAGER_ACTIVITY,
                rec.assigned_to,
                rec._awaiting_manager_todo_summary(),
            )

    # ---------------------------------------------------------------------
    # Record contract data (to_approve → approved)
    # ---------------------------------------------------------------------
    def _record_contract_todo_summary(self):
        self.ensure_one()
        return _(
            "แบบรายงานขอให้จัดซื้อจัดจ้าง (พจ.1) "
            "ได้รับอนุมัติให้จัดซื้อจัดจ้างแล้ว "
            "กรุณาตรวจสอบเพื่อบันทึกข้อมูลสัญญา/ใบสั่งซื้อ/จ้างภายในระบบ"
        )

    def _schedule_record_contract_todo(self):
        """The procurement officer (assigned_to on the PR) is the recipient —
        they will record the contract / PO data after PA approval."""
        for rec in self:
            pr = rec.request_id
            recipient = pr.assigned_to if pr else rec.user_id
            if not recipient:
                continue
            rec._schedule_personal_todo(
                PA_APPROVED_RECORD_CONTRACT_ACTIVITY,
                recipient,
                rec._record_contract_todo_summary(),
            )

    # ---------------------------------------------------------------------
    # State-transition hooks
    # ---------------------------------------------------------------------
    def button_to_approve(self):
        res = super().button_to_approve()
        self.filtered(
            lambda r: r.state == "to_approve"
        )._schedule_awaiting_manager_todo()
        return res

    def _on_sarabun_circulating(self, document):
        # PA has its own sarabun.document.mixin; Sarabun writes state=to_approve
        # directly (bypassing button_to_approve), so schedule the Todo here too.
        res = super()._on_sarabun_circulating(document)
        self.filtered(
            lambda r: r.state == "to_approve"
        )._schedule_awaiting_manager_todo()
        return res

    def _on_sarabun_rejected(self, document, step):
        res = super()._on_sarabun_rejected(document, step)
        self.activity_unlink([PA_AWAITING_MANAGER_ACTIVITY])
        return res

    def _on_sarabun_returned(self, document, step):
        res = super()._on_sarabun_returned(document, step)
        self.activity_unlink([PA_AWAITING_MANAGER_ACTIVITY])
        return res

    def _on_sarabun_cancelled(self, document):
        res = super()._on_sarabun_cancelled(document)
        self.activity_unlink([PA_AWAITING_MANAGER_ACTIVITY])
        return res

    def button_approved(self):
        res = super().button_approved()
        # UC3 FYI to requester (existing behaviour).
        self._notify_requester_fyi(_("approved"))
        # Manager consideration is genuinely complete → Completed history.
        self.activity_feedback([PA_AWAITING_MANAGER_ACTIVITY])
        # PR endorsement-approved Todo (created at Sarabun sign-off) rolls into
        # the record-contract Todo as the same action across both documents.
        pr_records = self.mapped("request_id")
        pr_records.activity_feedback([PR_ENDORSEMENT_APPROVED_ACTIVITY])
        # Next-actor Todo: record contract / PO data.
        self._schedule_record_contract_todo()
        return res

    def button_rejected(self):
        res = super().button_rejected()
        self._notify_requester_fyi(_("rejected"))
        return res

    def _action_do_reject(self, reason):
        res = super()._action_do_reject(reason)
        # Manager rejected — drop the pending consideration Todo silently.
        self.activity_unlink([PA_AWAITING_MANAGER_ACTIVITY])
        return res

    def _action_do_cancel(self, reason):
        res = super()._action_do_cancel(reason)
        self.activity_unlink(
            [
                PA_AWAITING_MANAGER_ACTIVITY,
                PA_APPROVED_RECORD_CONTRACT_ACTIVITY,
            ]
        )
        return res
