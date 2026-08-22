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

    # --- hooks ---------------------------------------------------------
    def _get_sarabun_document_type(self):
        return self.env.ref(
            "budget_support_request_sarabun.document_type_budget_support_request",
            raise_if_not_found=False,
        ) or super()._get_sarabun_document_type()

    def _sarabun_submit_guard(self):
        self.ensure_one()
        return self.state == "submitted"

    def _get_sarabun_subject(self):
        self.ensure_one()
        return _(
            "ขออนุมัติสนับสนุนงบประมาณ %(dept)s ประจำปีงบประมาณ พ.ศ. %(fy)s"
        ) % {
            "dept": self._sarabun_dim_name(self.department_analytic_id),
            "fy": self.account_fiscal_year_id.name or "",
        }

    def _get_sarabun_content(self):
        self.ensure_one()
        body = _(
            "ด้วย%(dept)s มีความประสงค์ขอรับการสนับสนุนงบประมาณ "
            "ประจำปีงบประมาณ พ.ศ. %(fy)s จำนวนเงิน %(amt)s บาท "
            "เลขที่คำขอ %(no)s โดยมีเหตุผลความจำเป็นดังนี้"
        ) % {
            "dept": self._sarabun_dim_name(self.department_analytic_id),
            "fy": self.account_fiscal_year_id.name or "",
            "amt": "{:,.2f}".format(self.amount_requested),
            "no": self.name or "",
        }
        return "<p>%s</p>%s" % (body, self.reason or "")

    @staticmethod
    def _sarabun_dim_name(analytic):
        name = (analytic.complete_name or analytic.name or "") if analytic else ""
        return name.replace(" / ", " ")

    # --- submit: wrap super() to set content + enclose the attachments ---
    def action_submit_to_sarabun(self):
        action = super().action_submit_to_sarabun()
        if action and action.get("res_id"):
            document = self.env["sarabun.document"].browse(action["res_id"])
            document.sudo().write(
                {
                    "include_content": True,
                    "content": self._get_sarabun_content(),
                    "enclosure_attachment_ids": [(6, 0, self.attachment_ids.ids)],
                }
            )
        return action

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
                request.show_reset_button = (
                    request.user_id == self.env.user or is_admin
                )
            elif request.state == "rejected":
                request.show_reset_button = is_manager or is_admin
            request.show_approve_button = is_manager or is_admin

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

    def action_approve(self):
        """Restricted to `submitted` — from `sent` a letter is already
        circulating (approving here would race with
        `_on_sarabun_completed`); from other states it would double-approve
        or revive a decided request through the back door."""
        if self.filtered(lambda r: r.state != "submitted"):
            raise UserError(_("Only submitted requests can be approved."))
        return super().action_approve()
