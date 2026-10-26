from odoo import _, fields, models
from odoo.exceptions import UserError


class BudgetSupportRequest(models.Model):
    """Route a budget.support.request for approval (ขออนุมัติสนับสนุนงบประมาณ)
    through e-Saraban — mirrors ``budget_transfer_sarabun`` exactly. The base
    ``budget_support_request`` only declares the extra ``sent``/``returned``/
    ``rejected`` states; this module owns everything specific to them.
    """

    _name = "budget.support.request"
    _inherit = ["budget.support.request", "sarabun.document.mixin"]

    state = fields.Selection(
        selection_add=[
            ("sent", "กำลังเวียนสารบรรณ"),
            ("approved",),
            ("returned", "ตีกลับเพื่อแก้ไข"),
            ("rejected", "ปฏิเสธ"),
            ("cancelled",),
        ],
        ondelete={
            "sent": "set default",
            "returned": "set default",
            "rejected": "set default",
        },
    )
    # เลขที่หนังสือ — filled from the หนังสือ when it is numbered (see
    # ``SarabunDocument._assign_register_number``), or typed in by hand when the
    # request was signed on paper outside the system and approved via the
    # manual fallback.
    sarabun_document_number = fields.Char(
        string="เลขที่หนังสือ",
        copy=False,
        index="trigram",
        tracking=True,
        help="Filled automatically when the e-Saraban หนังสือ is numbered; typed in "
        "by hand when the request was approved on paper outside the system.",
    )

    # --- hooks ---------------------------------------------------------
    def _get_sarabun_document_type(self):
        return (
            self.env.ref(
                "budget_support_request_sarabun.document_type_budget_support_request",
                raise_if_not_found=False,
            )
            or super()._get_sarabun_document_type()
        )

    def _sarabun_submit_guard(self):
        self.ensure_one()
        return self.state == "submitted"

    def _get_sarabun_subject(self):
        self.ensure_one()
        return _("ขอรับการสนับสนุน%(source)sสถาบัน ประจำปีงบประมาณ พ.ศ. %(fy)s เพิ่มเติม") % {
            "source": self.source_analytic_id.name or "",
            "fy": self.account_fiscal_year_id.name or "",
        }

    def _get_sarabun_addressee(self):
        """เรียน — like a budget transfer, a support request is decided by the
        อธิการบดี, so the หนังสือ is addressed to them."""
        return _("อธิการบดี")

    def _get_sarabun_body_template(self):
        """The live คำขอ figures, rendered between the หนังสือ's เนื้อหา and the
        signatures (agx_sarabun ADR-0015). Kept out of the editable ``content``
        on purpose: ``content`` is seeded once at create and owned by the
        drafter from then on, so a request revised after a ตีกลับ and re-sent on
        the same หนังสือ would otherwise go out for signature still showing the
        superseded amount."""
        return "budget_support_request_sarabun.report_budget_support_request_body"

    def _get_sarabun_content(self):
        """The editable บันทึกนำ seeding เนื้อหา — narrative only. Every
        authoritative figure (amount, request number, fiscal year) renders live
        from :meth:`_get_sarabun_body_template` instead."""
        self.ensure_one()
        body = _(
            "ด้วย%(dept)s มีความประสงค์ขอรับการสนับสนุนงบประมาณ "
            "ตามรายละเอียดที่แนบท้ายนี้ โดยมีเหตุผลความจำเป็นดังนี้"
        ) % {"dept": self._sarabun_dim_name(self.department_analytic_id)}
        return "<p>%s</p>%s" % (body, self.reason or "")

    @staticmethod
    def _sarabun_dim_name(analytic):
        name = (analytic.complete_name or analytic.name or "") if analytic else ""
        return name.replace(" / ", " ")

    def _prepare_transfer_vals(self):
        """The transfer posts on the strength of this request's หนังสือ (no
        letter of its own), so it carries that letter's number. The field
        comes from budget_transfer_sarabun's เลขที่หนังสือ (PR #1570) — skipped
        until that is installed."""
        vals = super()._prepare_transfer_vals()
        if "sarabun_document_number" in self.env["budget.transfer"]._fields:
            vals["sarabun_document_number"] = self.sarabun_document_number
        return vals

    # --- submit: wrap super() to enclose the attachments -----------------
    def action_submit_to_sarabun(self):
        action = super().action_submit_to_sarabun()
        if action and action.get("res_id"):
            document = self.env["sarabun.document"].browse(action["res_id"])
            # content + include_content are already seeded by the mixin's
            # _prepare_sarabun_document_vals from _get_sarabun_content(); เรียน
            # has no such hook, so it is set here.
            document.sudo().write(
                {
                    "addressee": self._get_sarabun_addressee(),
                    "enclosure_attachment_ids": [
                        (6, 0, self._copy_attachments_to_sarabun(document).ids)
                    ],
                }
            )
        return action

    def _copy_attachments_to_sarabun(self, document):
        """Enclose *copies* of the request's เอกสารแนบ, owned by the หนังสือ.

        Linking the request's own ``ir.attachment`` records would gate the
        enclosures on read access to ``budget.support.request``; a signing
        position holder normally reaches e-Saraban only. Copies stamped onto
        ``sarabun.document`` are readable by anyone who can read the letter
        (mirrors ``budget_transfer_sarabun._attach_transfer_pdf_enclosure``).
        """
        self.ensure_one()
        copies = self.env["ir.attachment"].sudo()
        for attachment in self.attachment_ids.sudo():
            # ``raw`` is passed explicitly so the copy carries the file content
            # regardless of how the store is configured (filestore vs db_datas).
            copies |= attachment.copy(
                {
                    "res_model": "sarabun.document",
                    "res_id": document.id,
                    "raw": attachment.raw,
                }
            )
        return copies

    # --- lifecycle callbacks ------------------------------------------
    def _on_sarabun_circulating(self, document):
        if self.state in ("submitted", "returned"):
            self.write({"state": "sent"})
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        final = document._signature_steps()[-1:]
        self.write(
            {
                "state": "approved",
                "approver_id": final.acted_by_id.id or False,
                "approval_date": document.signed_at,
            }
        )
        self._after_approved()
        return super()._on_sarabun_completed(document)

    def _on_sarabun_returned(self, document, step):
        self.state = "returned"
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_rejected(self, document, step):
        self.state = "rejected"
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_cancelled(self, document):
        self.state = "submitted"  # letter voided; ready to re-issue
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_report_action(self):
        return False  # no source report — the letter's own content is the body

    # --- editability + button visibility for the bridge-owned states ----
    def _compute_can_edit(self):
        """Reopen editing for a ``returned`` (ตีกลับ) request — the whole
        request is revised before the letter is re-sent."""
        super()._compute_can_edit()
        for request in self:
            if request.state == "returned":
                request.can_edit = True

    def _compute_button_visibility(self):
        """Extend the base compute for `returned`/`rejected` — states the
        base itself never reaches, so its own compute leaves every button
        hidden for them. `sent` intentionally stays all-hidden here too:
        deal with the live letter (ดึงกลับ/ยกเลิกการส่ง), not this form's
        own buttons."""
        super()._compute_button_visibility()
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        for request in self:
            if request.state == "returned":
                request.show_cancel_button = True
                request.show_reset_button = request.user_id == self.env.user or is_admin
            elif request.state == "rejected":
                request.show_reset_button = is_manager or is_admin

    # --- extra guards for the states this bridge introduces -------------
    def action_cancel(self):
        """Block from `sent` — a live letter must be pulled back or voided
        first, or the request and the letter states would diverge."""
        if self.filtered(lambda r: r.state == "sent"):
            raise UserError(
                _(
                    "This request has a letter out for signature. Recall "
                    "or void it before cancelling."
                )
            )
        return super().action_cancel()

    def action_reset_to_draft(self):
        """Block from `sent` (as above); a `rejected` request is revived by
        a manager/admin only, mirroring the base's `cancelled` gate."""
        if self.filtered(lambda r: r.state == "sent"):
            raise UserError(
                _(
                    "This request has a letter out for signature. Recall "
                    "or void it before resetting to draft."
                )
            )
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        if self.filtered(lambda r: r.state == "rejected") and not (
            is_manager or is_admin
        ):
            raise UserError(
                _("Only Budget Managers can reset a rejected request to draft.")
            )
        return super().action_reset_to_draft()

    def _check_no_live_sarabun_document(self):
        """The manual Approve fallback must not run behind a หนังสือ that is
        still around (a draft not yet sent, or one mid-circulation) — the
        letter's own callbacks would later overwrite the approval (a ตีกลับ
        would drag an approved, possibly already-fulfilled request back to
        `returned`). Force the user to delete/void the หนังสือ first."""
        if self.filtered("sarabun_has_live_document"):
            raise UserError(
                _(
                    "มีหนังสือสารบรรณค้างอยู่ ไม่สามารถอนุมัติได้ "
                    "กรุณาลบหรือยกเลิกหนังสือก่อนจึงจะอนุมัติด้วยตนเองได้"
                )
            )

    def action_approve(self):
        """Restricted to `submitted` — from `sent` a letter is already
        circulating (approving here would race with
        `_on_sarabun_completed`); from other states it would double-approve
        or revive a decided request through the back door."""
        if self.filtered(lambda r: r.state != "submitted"):
            raise UserError(_("Only submitted requests can be approved."))
        self._check_no_live_sarabun_document()
        return super().action_approve()


class SarabunDocument(models.Model):
    _inherit = "sarabun.document"

    def _assign_register_number(self):
        """Mirror the issued number onto the originating support request
        (sudo: the signer usually has no rights on the request)."""
        res = super()._assign_register_number()
        if self.origin_model == "budget.support.request" and self.origin_res_id:
            self.env["budget.support.request"].sudo().browse(
                self.origin_res_id
            ).sarabun_document_number = self.name
        return res
