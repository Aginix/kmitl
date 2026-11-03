from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Set while a cascade runs, so the sarabun hooks it triggers don't start another.
CASCADING = "pr_flow_cascading"
RECALL_STATES = ("to_verify", "to_verify_budget", "to_approve", "sent")
# e-GP: the owner may recall from here once e-GP is recorded as cancelled.
EGP_STATES = ("in_egp", "in_progress")
PRE_SENT_STATES = ("draft", "to_verify", "to_verify_budget", "to_approve")


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    egp_status = fields.Selection(
        selection_add=[("cancelled", "e-GP ถูกยกเลิก")],
        ondelete={"cancelled": "set null"},
    )
    flow_is_owner = fields.Boolean(
        compute="_compute_flow_is_owner",
        help="ผู้รับผิดชอบคำขอ (user_id) — ดึงกลับ/ยกเลิกได้",
    )

    @api.depends("user_id")
    @api.depends_context("uid")
    def _compute_flow_is_owner(self):
        for rec in self:
            rec.flow_is_owner = rec.user_id == self.env.user

    def _compute_sarabun_documents(self):
        super()._compute_sarabun_documents()
        # After e-GP ยกเลิก the previous round's completed หนังสือ stays on file
        # but must not block issuing the next round's หนังสือ.
        for rec in self:
            if rec.state in PRE_SENT_STATES and rec._flow_previous_round_only(
                rec.sarabun_document_ids
            ):
                rec.sarabun_has_live_document = False

    @api.model
    def _flow_previous_round_only(self, documents):
        live = documents.filtered(lambda d: d.state not in ("rejected", "cancelled"))
        return bool(live) and all(d.state == "completed" for d in live)

    # === Guards ===

    def _flow_check_owner(self):
        if self.env.su:
            return
        for rec in self:
            if not rec.flow_is_owner:
                raise UserError(
                    _("เฉพาะผู้รับผิดชอบคำขอ (%s) เท่านั้นที่ทำรายการนี้ได้")
                    % rec.user_id.name
                )

    def _flow_check_cancel(self):
        self._flow_check_owner()
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("ยกเลิกได้เฉพาะคำขอที่เป็นแบบร่าง — กรุณากลับแบบร่างก่อน")
                )

    def _flow_check_recall(self):
        """กลับแบบร่าง: shown at every step, allowed only while the หนังสือ is
        draft/returned (or none) — or, for e-GP, once e-GP is cancelled."""
        self._flow_check_owner()
        for rec in self:
            if rec.state in EGP_STATES and rec.is_egp:
                if rec.egp_status != "cancelled":
                    raise UserError(_("กลับแบบร่างได้เมื่อ e-GP ถูกยกเลิกแล้วเท่านั้น"))
                continue
            if rec.state not in RECALL_STATES:
                raise UserError(_("คำขอสถานะนี้กลับแบบร่างไม่ได้"))
            if rec.sarabun_state not in (False, "draft", "returned", "rejected", "cancelled"):
                raise UserError(
                    _("หนังสืออยู่สถานะ \"%s\" — กลับแบบร่างได้เมื่อหนังสือเป็นร่างหรือรอการแก้ไข")
                    % dict(rec._fields["sarabun_state"].selection).get(rec.sarabun_state)
                )

    def button_draft(self):
        if not self.env.context.get("pr_flow_reset"):
            for rec in self:
                if rec.state in ("cancelled", "rejected"):
                    raise UserError(_("คำขอที่ยกเลิกหรือถูกปฏิเสธแล้ว กลับแบบร่างไม่ได้"))
                if rec.sarabun_state in ("circulating", "completed"):
                    raise UserError(
                        _("หนังสือของคำขอนี้อยู่ระหว่างเวียนหรือเสร็จสิ้นแล้ว กลับแบบร่างไม่ได้")
                    )
        return super().button_draft()

    # === The two entry points every step back goes through ===

    def _reset_to_draft(self, reason, label):
        """กลับแบบร่าง / ตีกลับ / หนังสือถูกตีกลับ → draft.

        ``button_draft`` releases this request's own ใบจอง (a drawn or
        project/plan one is only detached or kept, see purchase_request_budget),
        so the next pass reserves again. Callers check permissions first; the
        release then runs sudo, because the budget override swallows an access
        error and would silently keep the ใบจอง."""
        for rec in self:
            rec.message_post(
                body=_("%(label)s คำขอ (พ.1) %(pr)s เหตุผล: %(reason)s")
                % {"label": label, "pr": rec.name, "reason": reason},
                subtype_xmlid="mail.mt_note",
            )
        return self.sudo().with_context(pr_flow_reset=True).button_draft()

    def _cancel_all(self, reason, label=None):
        """ยกเลิกทั้งหมด: พ.1, its พจ.1, all their หนังสือ and the ใบจอง."""
        if self.env.context.get(CASCADING):
            return
        label = label or _("ยกเลิก")
        # sudo after the callers' guards: the cascade touches ใบจอง/หนังสือ the
        # acting user has no rights on.
        for rec in self.sudo().with_context(**{CASCADING: True}):
            rec.message_post(
                body=_("%(label)s คำขอ (พ.1) %(pr)s ทั้งชุด เหตุผล: %(reason)s")
                % {"label": label, "pr": rec.name, "reason": reason},
                subtype_xmlid="mail.mt_note",
            )
            approvals = rec.request_approval_ids.filtered(
                lambda a: a.state not in ("cancelled", "rejected")
            )
            for approval in approvals:
                approval._flow_void_sarabun(reason)
                approval.message_post(
                    body=_("%(label)s พจ.1 ตามคำขอ %(pr)s เหตุผล: %(reason)s")
                    % {"label": label, "pr": rec.name, "reason": reason},
                    subtype_xmlid="mail.mt_note",
                )
                approval.activity_ids.unlink()
                approval.write({"state": "cancelled"})
            rec._flow_void_sarabun(reason)
            rec._flow_release_budget()
            rec.activity_ids.unlink()
            rec.write({"state": "cancelled"})

    def _flow_release_budget(self):
        for rec in self:
            commitment = rec.budget_commitment_id
            if commitment and commitment.state != "cancel":
                rec._cancel_budget_commitment()
                rec.message_post(
                    body=_("ปล่อยใบจองเงิน %s") % commitment.display_name,
                    subtype_xmlid="mail.mt_note",
                )

    # === Buttons ===

    def action_open_flow_wizard(self):
        self.ensure_one()
        mode = self.env.context.get("flow_mode", "recall")
        if mode == "recall":
            self._flow_check_recall()
        else:
            self._flow_check_egp_cancel()
        return {
            "type": "ir.actions.act_window",
            "name": _("กลับแบบร่าง") if mode == "recall" else _("บันทึก e-GP ถูกยกเลิก"),
            "res_model": "purchase.request.flow.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id, "default_mode": mode},
        }

    def action_flow_recall(self, reason):
        """กลับแบบร่าง by the owner (user_id), with a reason."""
        self.ensure_one()
        self._flow_check_recall()
        egp_round = self.state in EGP_STATES
        self._reset_to_draft(reason, _("กลับแบบร่าง"))
        if egp_round:
            # The completed หนังสือ stays as the previous round's record; the
            # next round issues a new one.
            self.write({"egp_status": False})
        return True

    def button_cancel(self):
        # Deliberately not chained: purchase_request_budget's override released
        # the ใบจอง as soon as this dialog opened, even if it was then closed.
        self.ensure_one()
        self._flow_check_cancel()
        return {
            "type": "ir.actions.act_window",
            "name": _("ยกเลิกคำขอ (พ.1)"),
            "res_model": "purchase.request.cancel.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_request_id": self.id},
        }

    def _action_do_cancel(self, reason):
        self.ensure_one()
        self._flow_check_cancel()
        self._cancel_all(reason)

    def _action_do_return_to_draft(self, reason):
        """ตีกลับ goes straight to draft (and releases the ใบจอง), replacing the
        one-step-back of ADR-0010."""
        self.ensure_one()
        if self.state == "to_verify":
            self._check_can_verify()
        elif self.state == "to_verify_budget":
            self._check_can_commit_budget()
        else:
            raise UserError(_("ตีกลับได้เฉพาะขั้นรอตรวจสอบและรอยืนยันงบประมาณ"))
        return self._reset_to_draft(reason, _("ตีกลับ"))

    def action_submit_to_sarabun(self):
        self.ensure_one()
        if self.state != "to_approve":
            raise UserError(_("สร้างหนังสือได้เมื่อจองงบประมาณแล้ว (รอส่งหนังสือ)"))
        if self._flow_previous_round_only(self.sudo().sarabun_document_ids):
            # New round after e-GP ยกเลิก: a new หนังสือ, the old one stays completed.
            action = self.action_create_sarabun_document()
            document = self.env["sarabun.document"].browse(action["res_id"])
            self._sarabun_post("submitted", document)
            self._copy_attachments_to_sarabun(document)
            return action
        return super().action_submit_to_sarabun()

    def action_resend_to_sarabun(self):
        self.ensure_one()
        if self.state != "to_approve":
            raise UserError(
                _("ส่งหนังสือใหม่ได้เมื่อคำขอผ่านการตรวจสอบและจองงบประมาณใหม่แล้ว (รอส่งหนังสือ)")
            )
        return super().action_resend_to_sarabun()

    def _flow_check_egp_cancel(self):
        self.ensure_one()
        if not (self.env.su or self.env.user.has_group("purchase.group_purchase_user")):
            raise UserError(_("เฉพาะเจ้าหน้าที่พัสดุเท่านั้นที่บันทึก e-GP ถูกยกเลิกได้"))
        if not (
            self.is_egp
            and self.state in EGP_STATES
            and self.egp_status in ("waiting", "in_progress")
        ):
            raise UserError(_("บันทึก e-GP ถูกยกเลิกได้เฉพาะคำขอที่อยู่ในกระบวนการ e-GP"))
        orders = self.line_ids.purchase_lines.order_id.filtered(
            lambda o: o.state != "cancel"
        )
        if orders:
            raise UserError(
                _("มีใบสั่งซื้อที่ยังไม่ยกเลิก (%s) — กรุณายกเลิกใบสั่งซื้อก่อน")
                % ", ".join(orders.mapped("name"))
            )

    def action_egp_cancel(self, reason):
        """e-GP ถูกยกเลิก: recorded by the procurement officer; the owner then
        brings the request back to draft with กลับแบบร่าง."""
        self._flow_check_egp_cancel()
        self.message_post(
            body=_("e-GP ถูกยกเลิก เหตุผล: %s") % reason, subtype_xmlid="mail.mt_note"
        )
        self.write({"egp_status": "cancelled"})
        return True

    # === Sarabun outcomes ===

    def _on_sarabun_returned(self, document, step):
        res = super()._on_sarabun_returned(document, step)
        reason = (
            (step and step.note)
            or self.env.context.get("pr_flow_reason")
            or document.display_name
        )
        self._reset_to_draft(reason, _("หนังสือถูกตีกลับ"))
        return res

    def _on_sarabun_rejected(self, document, step):
        # Not chained: purchase_request_sarabun only marks the request rejected.
        # ปฏิเสธ ends everything: พ.1, ใบจอง and the หนังสือ itself.
        self._sarabun_post("rejected", document, step)
        self._cancel_all((step and step.note) or document.display_name, _("ปฏิเสธ"))

    def _on_sarabun_cancelled(self, document):
        if self.env.context.get(CASCADING):
            return
        # Not chained: purchase_request_sarabun's handler goes through the
        # draft-only cancel dialog path.
        self._sarabun_post("cancelled", document)
        self._cancel_all(_("ยกเลิกการส่งหนังสือ %s") % document.display_name)

    # === พจ.1 auto-created after the หนังสือ completes ===

    def _transition_after_sarabun_approve(self):
        return super(
            PurchaseRequest, self.with_context(pr_flow_auto_pa=True)
        )._transition_after_sarabun_approve()

    def button_create_approval(self):
        rec = self
        if self.env.context.get("pr_flow_auto_pa"):
            creator = self.company_id.pa_auto_creator_id or self.env.ref(
                "base.user_root"
            )
            rec = self.with_user(creator).sudo().with_context(pr_flow_auto_pa=False)
        return super(PurchaseRequest, rec).button_create_approval()
