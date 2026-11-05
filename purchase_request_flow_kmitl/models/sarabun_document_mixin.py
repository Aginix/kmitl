from odoo import _, models


class SarabunDocumentMixin(models.AbstractModel):
    _inherit = "sarabun.document.mixin"

    def _flow_void_sarabun(self, reason):
        """Cancel every หนังสือ of this record as part of ยกเลิกทั้งหมด (the
        number is voided). Written directly, so no origin hook fires back into
        the cascade."""
        for rec in self:
            for doc in rec.sudo().sarabun_document_ids:
                if doc.state == "cancelled":
                    continue
                doc.routing_step_ids._clear_activities()
                doc.routing_step_ids.filtered(
                    lambda s: s.state in ("waiting", "active")
                ).write({"state": "skipped"})
                was_rejected = doc.state == "rejected"  # number already voided
                doc.state = "cancelled"
                if not was_rejected:
                    doc._void_register("cancelled")
                doc.message_post(
                    body=_("ยกเลิกหนังสือตามการยกเลิก %(origin)s เหตุผล: %(reason)s")
                    % {"origin": rec.display_name, "reason": reason},
                    subtype_xmlid="mail.mt_note",
                )
