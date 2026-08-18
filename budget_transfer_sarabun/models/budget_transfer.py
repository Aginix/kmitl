import base64

from odoo import _, models


class BudgetTransfer(models.Model):
    """Route a budget.transfer for approval (ขออนุมัติโอนงบประมาณ) through
    e-Saraban (ADR-0014). The transfer owns its own 7-state lifecycle
    (budget_transfer); this bridge only wires the หนังสือ: it creates the
    Document at ``submitted``, encloses the printed แบบ งปม.303 as สิ่งที่ส่ง
    มาด้วย, and maps the หนังสือ outcome back onto the transfer state.
    """

    _name = "budget.transfer"
    _inherit = ["budget.transfer", "sarabun.document.mixin"]

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
        return "<p>%s</p>" % body

    @staticmethod
    def _sarabun_dim_name(analytic):
        name = (analytic.complete_name or analytic.name or "") if analytic else ""
        return name.replace(" / ", " ")

    # --- submit: wrap super() to set content + enclose งปม.303 ----------
    def action_submit_to_sarabun(self):
        action = super().action_submit_to_sarabun()
        if action and action.get("res_id"):
            document = self.env["sarabun.document"].browse(action["res_id"])
            document.sudo().write({"content": self._get_sarabun_content()})
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
