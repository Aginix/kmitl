from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _name = "purchase.request"
    _inherit = [
        "purchase.request",
        "sarabun.document.mixin",
        "portal.mixin",
        "thai.date.mixin",
    ]

    state = fields.Selection(
        # หมุดท้ายต้องเป็น approved ไม่ใช่ in_progress: approved ของ OCA คั่นอยู่
        # ระหว่าง to_approve กับ in_progress อยู่แล้ว ข้อจำกัด sent < in_progress
        # จึงไม่ได้ห้าม approved/in_egp/in_approval แทรกมาก่อน sent
        # (merge_sequences เป็น topological sort — คู่ที่ติดกันคือข้อจำกัดเดียวที่มี)
        selection_add=[("to_approve",), ("sent", "Sent"), ("approved",)],
        ondelete={"sent": "set default"},
    )

    def _compute_access_url(self):
        """Compute the access URL for portal access."""
        super()._compute_access_url()
        for request in self:
            request.access_url = f"/my/purchase_request/{request.id}"

    def _get_report_base_filename(self):
        self.ensure_one()
        return "Purchase Request-%s" % (self.name)

    def open_preview(self):
        if self.id:
            return {
                "type": "ir.actions.act_url",
                "url": self.access_url,
                "target": "new",
            }

    def _get_sarabun_subject(self):
        return self.title

    def _get_sarabun_sender_department(self):
        return (
            self.requested_by.employee_id.department_id
            or super()._get_sarabun_sender_department()
        )

    def _on_sarabun_circulating(self, document):
        # The หนังสือ outlives a pull-back of the พ.1 (root ADR-0014), so it may
        # only go out while the พ.1 waits for it — raising rolls the send back.
        if self.state != "to_approve":
            raise UserError(
                _("ส่งหนังสือได้เฉพาะเมื่อคำขอ (พ.1) %s อยู่สถานะรออนุมัติ") % self.name
            )
        self.write({"state": "sent"})
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        self._transition_after_sarabun_approve()
        self.message_post(
            body=_("Approved via Sarabun document: %s") % document.name,
        )
        return super()._on_sarabun_completed(document)

    def _on_sarabun_rejected(self, document, step):
        self.button_rejected()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_returned(self, document, step):
        self._action_do_return(post_message=False)
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_recalled(self, document):
        """ดึงกลับ (แก้ไข) by the sender (root ADR-0014): the พ.1 goes back to
        waiting for its หนังสือ, which is edited and re-sent — not to ``returned``.
        A recall from any other state (admin Reset) keeps the ตีกลับ handling."""
        if self.state != "sent":
            return super()._on_sarabun_recalled(document)
        self.write({"state": "to_approve"})
        self.message_post(
            body=_("ดึงกลับหนังสือ %s มาแก้ไข") % document.name,
            subtype_xmlid="mail.mt_note",
        )

    def _on_sarabun_cancelled(self, document):
        self._action_do_cancel(_("ยกเลิกจากสารบรรณ: %s") % document.name)
        return super()._on_sarabun_cancelled(document)

    # ADR-0015: render through Sarabun's own no-source layout (สารบรรณ owns the
    # header — เลขที่/หน่วยงาน/เรียน/วันที่/อ้างถึง — and the endorsement block).
    # We therefore DON'T override _get_sarabun_report_action (mixin default →
    # False), and instead contribute:
    #   - the editable บรรยาย via _get_sarabun_content (seeded once at submit), and
    #   - the live tables (items / budget / attachments / committees) via
    #     _get_sarabun_body_template.

    def _get_sarabun_document_type(self):
        return (
            self.env.ref(
                "purchase_request_sarabun.document_type_purchase_request",
                raise_if_not_found=False,
            )
            or super()._get_sarabun_document_type()
        )

    def _get_sarabun_body_template(self):
        """The live body — items table, budget details, enclosure list, committee
        appointments — rendered between the หนังสือ's เนื้อหา and its signatures
        (ADR-0015). Kept live so the official หนังสือ can never show numbers that
        diverge from the reserved commitment."""
        return "purchase_request_sarabun.report_purchase_request_body"

    def _get_sarabun_content(self):
        """The editable บรรยาย seeding เนื้อหา (policy 5A: seeded once at submit,
        then owned by the user). The authoritative tables render live via
        _get_sarabun_body_template — never seeded here."""
        self.ensure_one()
        return self.env["ir.qweb"]._render(
            "purchase_request_sarabun.report_purchase_request_narrative",
            {"o": self.with_context(lang="th_TH")},
        )

    def action_submit_to_sarabun(self):
        """Also carry the request's เอกสารแนบ onto the หนังสือ as สิ่งที่ส่งมาด้วย.

        A หนังสือ still open from an earlier pass (draft, or returned by ตีกลับ /
        ดึงกลับ) is reused instead of spawning a new one (root ADR-0014)."""
        self.ensure_one()
        if self.state != "to_approve":
            raise UserError(_("สร้างหนังสือได้เฉพาะคำขอ (พ.1) ที่รออนุมัติ"))
        self._check_is_team()
        # Searched, not read off active_sarabun_document_id: that compute would be
        # cached empty and hide the หนังสือ created below from the caller.
        # Searched as sudo: another team member's หนังสือ is invisible to the user.
        document = (
            self.env["sarabun.document"]
            .sudo()
            .search(
                [
                    ("origin_model", "=", self._name),
                    ("origin_res_id", "=", self.id),
                    ("state", "in", ("draft", "returned")),
                ],
                order="id desc",
                limit=1,
            )
        )
        if document:
            # Only its sender edits and sends a หนังสือ; never fork a second one.
            if document.sender_user_id != self.env.user and not self.env.user.has_group(
                "agx_sarabun.group_sarabun_manager"
            ):
                raise UserError(
                    _(
                        "คำขอ (พ.1) นี้มีหนังสือ %(doc)s อยู่แล้ว "
                        "กรุณาให้ %(sender)s ผู้จัดทำหนังสือเป็นผู้แก้ไขและส่งต่อ"
                    )
                    % {
                        "doc": document.subject,
                        "sender": document.sender_user_id.name,
                    }
                )
            document.write({"subject": self._get_sarabun_subject()})
            return {
                "type": "ir.actions.act_window",
                "res_model": "sarabun.document",
                "res_id": document.id,
                "view_mode": "form",
                "target": "current",
            }
        action = super().action_submit_to_sarabun()
        if action and action.get("res_id"):
            document = self.env["sarabun.document"].browse(action["res_id"])
            self._copy_attachments_to_sarabun(document)
        return action

    def _copy_attachments_to_sarabun(self, document):
        """Copy the request's attachments onto the หนังสือ as enclosures. Copied
        (not merely referenced) with ``res_model=sarabun.document`` so a Route
        recipient without rights on the request can still open them — the หนังสือ's
        ACL governs. Seeded once at submit; the drafter then manages enclosures on
        the หนังสือ itself."""
        self.ensure_one()
        enclosures = self.env["ir.attachment"]
        for attachment in self.attachment_ids:
            enclosures |= attachment.sudo().copy(
                {"res_model": "sarabun.document", "res_id": document.id}
            )
        if enclosures:
            document.sudo().write(
                {"enclosure_attachment_ids": [(4, a.id) for a in enclosures]}
            )
