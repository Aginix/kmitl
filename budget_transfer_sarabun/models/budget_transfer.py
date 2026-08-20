import base64

from markupsafe import escape

from odoo import _, fields, models
from odoo.exceptions import UserError


class BudgetTransfer(models.Model):
    """Route a budget.transfer for approval (ขออนุมัติโอนงบประมาณ) through
    e-Saraban (ADR-0014). The base `budget_transfer` only declares the extra
    ``sent``/``returned``/``rejected`` states (a Selection must list every
    value a bridge may write) — this module owns everything specific to
    them: creating the หนังสือ, mapping its outcome back onto the transfer,
    the button visibility for those states, and the extra action guards
    (``sent`` has a live letter out for signature, so cancel/reset/approve/
    post must not race with it).
    """

    _name = "budget.transfer"
    _inherit = ["budget.transfer", "sarabun.document.mixin"]

    # The e-Saraban states the base doesn't need. Ordered via ``posted`` /
    # ``cancelled`` anchors so the statusbar reads draft → submitted → sent →
    # posted, with returned/rejected before cancelled. ``set default`` returns
    # any record still in one of these states to ``draft`` if this bridge is
    # ever uninstalled (base default), keeping the required field valid.
    state = fields.Selection(
        # Relabel ``submitted`` for the e-Saraban flow: here it means the data
        # is confirmed and merely waiting for the หนังสือ to be issued (via
        # "สร้างหนังสือ"), not that anything has been sent yet.
        selection_add=[
            ("submitted", "รอส่งขออนุมัติ"),
            ("sent", "กำลังเวียนสารบรรณ"),
            ("posted",),
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

    # --- hooks ---------------------------------------------------------
    def _get_sarabun_document_type(self):
        return self.env.ref(
            "budget_transfer_sarabun.document_type_budget_transfer",
            raise_if_not_found=False,
        ) or super()._get_sarabun_document_type()

    def _sarabun_submit_guard(self):
        self.ensure_one()
        return self.state == "submitted"

    def _get_sarabun_subject(self):
        self.ensure_one()
        return _(
            "ขออนุมัติโอน เปลี่ยนแปลง %(src)s ประจำปีงบประมาณ พ.ศ. %(fy)s %(dept)s"
        ) % {
            "src": self._sarabun_dim_name(self.source_analytic_id),
            "fy": self.account_fiscal_year_id.name or "",
            "dept": self._sarabun_dim_name(self.department_analytic_id),
        }

    def _get_sarabun_content(self):
        self.ensure_one()
        body = _(
            "ด้วย%(dept)s มีความประสงค์ขออนุมัติโอน เปลี่ยนแปลง %(src)s "
            "ประจำปีงบประมาณ พ.ศ. %(fy)s จำนวนเงิน %(amt)s บาท "
            "รายละเอียดตามเอกสารแนบ แบบ งปม. 303 เลขที่ %(no)s"
        ) % {
            "dept": self._sarabun_dim_name(self.department_analytic_id),
            "src": self._sarabun_dim_name(self.source_analytic_id),
            "fy": self.account_fiscal_year_id.name or "",
            "amt": "{:,.2f}".format(self.amount),
            "no": self.name or "",
        }
        content = "<p>%s</p>" % body
        # Carry the transfer's เหตุผลการขออนุมัติ into the letter body so the default
        # content is complete the moment the หนังสือ is created.
        if self.reason:
            reason_html = str(escape(self.reason)).replace("\n", "<br/>")
            content += "<p>%s<br/>%s</p>" % (_("เหตุผลการขออนุมัติ"), reason_html)
        return content

    def _get_sarabun_addressee(self):
        """เรียน — a budget transfer's approval หนังสือ is always addressed to
        the อธิการบดี (Rector), who approves the transfer."""
        return _("อธิการบดี")

    @staticmethod
    def _sarabun_dim_name(analytic):
        name = (analytic.complete_name or analytic.name or "") if analytic else ""
        return name.replace(" / ", " ")

    # --- submit: wrap super() to set content + enclose งปม.303 ----------
    def action_submit_to_sarabun(self):
        action = super().action_submit_to_sarabun()
        if action and action.get("res_id"):
            document = self.env["sarabun.document"].browse(action["res_id"])
            document.sudo().write(
                {
                    "content": self._get_sarabun_content(),
                    "addressee": self._get_sarabun_addressee(),
                }
            )
            self._attach_transfer_pdf_enclosure(document)
        return action

    def _attach_transfer_pdf_enclosure(self, document):
        self.ensure_one()
        pdf, _dummy = self.env["ir.actions.report"].sudo()._render_qweb_pdf(
            "budget_transfer_pdf.action_report_budget_transfer", self.ids,
        )
        attachment = self.env["ir.attachment"].sudo().create(
            {
                "name": "%s.pdf" % ((self.name or "budget-transfer").replace("/", "-")),
                "type": "binary",
                "datas": base64.b64encode(pdf),
                "mimetype": "application/pdf",
                "res_model": "sarabun.document",
                "res_id": document.id,
            }
        )
        document.sudo().write({"enclosure_attachment_ids": [(4, attachment.id)]})

    # --- lifecycle callbacks ------------------------------------------
    def _on_sarabun_circulating(self, document):
        if self.state in ("submitted", "returned"):
            # The transfer's own date field is hidden (ADR-0014 follow-up) —
            # it now tracks the letter's ลงวันที่ (re-stamped on every send),
            # not the moment the transfer was submitted in draft.
            self.write({"state": "sent", "date": document.date})
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        # ADR-0014: trust the confirm-time check, do NOT re-validate
        # availability — the reservation window is a known, accepted race
        # until transfers go through a budget reservation (deferred).
        self._post_transfer()  # sets state='posted'
        final = document._signature_steps()[-1:]
        self.write(
            {
                "approver_id": final.acted_by_id.id or False,
                "approval_date": document.signed_at,
            }
        )
        return super()._on_sarabun_completed(document)

    def _on_sarabun_returned(self, document, step):
        self.state = "returned"
        return super()._on_sarabun_returned(document, step)

    def _on_sarabun_rejected(self, document, step):
        self.state = "rejected"
        self.move_id.button_cancel()
        return super()._on_sarabun_rejected(document, step)

    def _on_sarabun_cancelled(self, document):
        self.state = "submitted"  # letter voided; ready to re-issue
        return super()._on_sarabun_cancelled(document)

    def _get_sarabun_report_action(self):
        return False  # default e-Saraban body; งปม.303 rides as enclosure

    # --- editability + button visibility for the bridge-owned states ----
    def _compute_can_edit(self):
        """Reopen editing for a ``returned`` (ตีกลับ) transfer — the whole
        header/lines are revised before the letter is re-sent. Every other
        state keeps the base rule (editable in ``draft`` only)."""
        super()._compute_can_edit()
        for transfer in self:
            if transfer.state == "returned":
                transfer.can_edit = True

    def _compute_button_visibility(self):
        """Extend the base compute for `returned`/`rejected` — states the
        base itself never reaches, so its own compute leaves every button
        hidden for them. `sent` intentionally stays all-hidden here too:
        deal with the live letter (ดึงกลับ/ยกเลิกการส่ง), not the transfer
        form's own buttons."""
        super()._compute_button_visibility()
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        for transfer in self:
            if transfer.state == "returned":
                transfer.show_cancel_button = True
                transfer.show_reset_button = (
                    transfer.user_id == self.env.user or is_admin
                )
            elif transfer.state == "rejected":
                transfer.show_reset_button = is_manager or is_admin
            # Manual approve fallback — only a manager/admin, and only while the
            # transfer is still `submitted`. Gating on the state keeps it hidden
            # once posted (approval flowed through the letter) or in any other
            # state, instead of the base's plain `state == 'submitted'` flag.
            transfer.show_approve_button = transfer.state == "submitted" and (
                is_manager or is_admin
            )

    # --- extra guards for the states this bridge introduces -------------
    def action_cancel(self):
        """Block from `sent` — a live letter must be pulled back or voided
        first, or the transfer and the letter states would diverge."""
        if self.filtered(lambda t: t.state == "sent"):
            raise UserError(
                _(
                    "This transfer has a letter out for signature. Recall "
                    "or void it before cancelling."
                )
            )
        return super().action_cancel()

    def action_reset_to_draft(self):
        """Block from `sent` (as above); a `rejected` transfer is revived
        by a manager/admin only, mirroring the base's `cancelled` gate."""
        if self.filtered(lambda t: t.state == "sent"):
            raise UserError(
                _(
                    "This transfer has a letter out for signature. Recall "
                    "or void it before resetting to draft."
                )
            )
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        if self.filtered(lambda t: t.state == "rejected") and not (
            is_manager or is_admin
        ):
            raise UserError(
                _("Only Budget Managers can reset a rejected transfer to draft.")
            )
        return super().action_reset_to_draft()

    def _check_no_live_sarabun_document(self):
        """The manual Approve & Post fallback must not run behind a หนังสือ that
        is still around (a draft not yet sent, or one mid-circulation) — that
        would leave the letter dangling against an already-posted transfer.
        Force the user to delete the หนังสือ first."""
        if self.filtered("sarabun_has_live_document"):
            raise UserError(
                _(
                    "มีหนังสือสารบรรณค้างอยู่ ไม่สามารถอนุมัติและบันทึกได้ "
                    "กรุณาลบหนังสือก่อนจึงจะดำเนินการด้วยตนเองได้"
                )
            )

    def action_approve(self):
        """Restricted to `submitted` — from `sent` a letter is already
        circulating (approving here would race with `_on_sarabun_completed`);
        from `posted`/`rejected`/`cancelled` it would double-post or revive
        a decided transfer through the back door."""
        if self.filtered(lambda t: t.state != "submitted"):
            raise UserError(_("Only submitted transfers can be approved."))
        self._check_no_live_sarabun_document()
        return super().action_approve()

    def action_post(self):
        """Same restriction as `action_approve` — see there."""
        if self.filtered(lambda t: t.state != "submitted"):
            raise UserError(_("Only submitted transfers can be posted."))
        self._check_no_live_sarabun_document()
        return super().action_post()
