from odoo import _, models
from odoo.exceptions import UserError

from .purchase_request import CASCADING

# Downstream documents that make a พจ.1 no longer cancellable, when the module
# providing them is installed.
DOWNSTREAM_FIELDS = (
    "disbursement_request_ids",
    "advance_payment_ids",
    "work_acceptance_ids",
)
DEAD_STATES = ("cancel", "cancelled", "rejected")


class PurchaseRequestApproval(models.Model):
    _inherit = "purchase.request.approval"

    def _flow_cancel_blockers(self):
        self.ensure_one()
        blockers = []
        orders = self.request_id.line_ids.purchase_lines.order_id.filtered(
            lambda o: o.state != "cancel"
        )
        if orders:
            blockers.append(_("ใบสั่งซื้อ: %s") % ", ".join(orders.mapped("name")))
        for record in (self, self.request_id):
            for fname in DOWNSTREAM_FIELDS:
                if fname not in record._fields:
                    continue
                live = record[fname].filtered(
                    lambda r: "state" not in r._fields or r.state not in DEAD_STATES
                )
                if live:
                    blockers.append(
                        "%s: %s"
                        % (
                            record._fields[fname].string,
                            ", ".join(live.mapped("display_name")),
                        )
                    )
        return blockers

    def _flow_check_blockers(self):
        for rec in self:
            blockers = rec._flow_cancel_blockers()
            if blockers:
                raise UserError(
                    _("ทำรายการไม่ได้ เพราะมีเอกสารที่ดำเนินการต่อแล้ว:\n%s")
                    % "\n".join(blockers)
                )

    def _flow_check_cancel(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("ยกเลิก พจ.1 ได้เฉพาะแบบร่าง — ถ้าอนุมัติแล้วให้กลับแบบร่างก่อน")
                )
        self._flow_check_blockers()

    def action_open_flow_draft_wizard(self):
        self.ensure_one()
        self._flow_check_to_draft()
        return {
            "type": "ir.actions.act_window",
            "name": _("กลับแบบร่าง พจ.1"),
            "res_model": "purchase.request.flow.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_approval_id": self.id, "default_mode": "pa_draft"},
        }

    def _flow_check_to_draft(self):
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("กลับแบบร่างได้เฉพาะ พจ.1 ที่อนุมัติแล้ว"))
        self._flow_check_blockers()

    def action_flow_to_draft(self, reason):
        """พจ.1 อนุมัติแล้วแต่อยากยกเลิก: back to draft first, then ยกเลิก."""
        self.ensure_one()
        self._flow_check_to_draft()
        self.message_post(
            body=_("กลับแบบร่าง พจ.1 %(pa)s เหตุผล: %(reason)s")
            % {"pa": self.name, "reason": reason},
            subtype_xmlid="mail.mt_note",
        )
        self.write({"state": "draft"})
        if self.request_id.state == "in_progress":
            self.request_id.sudo().write({"state": "in_approval"})
        return True

    def button_cancel(self):
        self._flow_check_cancel()
        return super().button_cancel()

    def _action_do_cancel(self, reason):
        """ยกเลิก พจ.1 (draft only) cancels everything."""
        self.ensure_one()
        self._flow_check_cancel()
        if self.request_id:
            self.request_id._cancel_all(reason)
        else:
            self._flow_void_sarabun(reason)
            self.write({"state": "cancelled"})

    def action_resend_to_sarabun(self):
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("ส่งหนังสือใหม่ได้เฉพาะ พจ.1 ที่เป็นแบบร่าง"))
        return super().action_resend_to_sarabun()

    def _on_sarabun_returned(self, document, step):
        res = super()._on_sarabun_returned(document, step)
        self.write({"state": "draft"})
        return res

    def _on_sarabun_rejected(self, document, step):
        # Not chained: the base only rejects the PA and marks the PR rejected;
        # ปฏิเสธ cancels everything.
        self._sarabun_post("rejected", document, step)
        reason = (step and step.note) or document.display_name
        if self.request_id:
            self.request_id._cancel_all(reason, _("ปฏิเสธ"))
        else:
            self.write({"state": "cancelled"})

    def _on_sarabun_cancelled(self, document):
        if self.env.context.get(CASCADING):
            return
        self._sarabun_post("cancelled", document)
        reason = _("ยกเลิกการส่งหนังสือ %s") % document.display_name
        if self.request_id:
            self.request_id._cancel_all(reason)
        else:
            self.write({"state": "cancelled"})
