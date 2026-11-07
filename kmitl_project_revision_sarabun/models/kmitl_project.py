from markupsafe import Markup, escape

from odoo import _, models
from odoo.exceptions import AccessError, UserError


class KmitlProject(models.Model):
    """A Revision Draft (ADR-0014) is approved by a หนังสือขออนุมัติปรับแผน: the
    draft's own หนังสือ, raised once it is รออนุมัติปรับแผน (``sent``). Live
    projects keep the kmitl_project_sarabun behaviour."""

    _inherit = "kmitl.project"

    def _get_sarabun_subject(self):
        if not self.revision_of_id:
            return super()._get_sarabun_subject()
        return _("ขออนุมัติปรับแผนโครงการ %(name)s (ฉบับที่ %(version)s)") % {
            "name": self.name or "",
            "version": self.revision_version,
        }

    def _get_sarabun_content(self):
        if not self.revision_of_id:
            return super()._get_sarabun_content()
        url = escape(self._get_sarabun_portal_url())
        return Markup(
            '<p style="text-indent: 2.5em;">%s</p>%s<p>%s <a href="%s">%s</a></p>'
        ) % (
            _("เหตุผลการปรับแผน: %s") % (self.revision_reason or ""),
            self._revision_expense_diff(),
            _("รายละเอียดโครงการ:"),
            url,
            _("เปิดดูในระบบ"),
        )

    def _get_sarabun_addressee(self):
        if not self.revision_of_id:
            return super()._get_sarabun_addressee()
        return self.revision_of_id._get_sarabun_addressee()

    def _get_sarabun_document_type(self):
        if not self.revision_of_id:
            return super()._get_sarabun_document_type()
        return self.env.ref(
            "kmitl_project_revision_sarabun.document_type_kmitl_project_revision"
        )

    def _get_sarabun_route_template(self):
        if not self.revision_of_id:
            return super()._get_sarabun_route_template()
        return False

    def _sarabun_submit_guard(self):
        if not self.revision_of_id:
            return super()._sarabun_submit_guard()
        self.ensure_one()
        if not self.can_submit_sarabun:
            raise AccessError(
                _("เฉพาะเจ้าของโครงการหรือเจ้าหน้าที่โครงการเท่านั้นที่สร้างหนังสือขออนุมัติปรับแผนได้")
            )
        return self.state == "sent" and not self.sarabun_has_live_document

    def _sarabun_circulating_document(self):
        """The draft's หนังสือ already out for signing (not a draft)."""
        self.ensure_one()
        return self._all_sarabun_documents().filtered(
            lambda d: d.state not in ("draft", "completed", "rejected", "cancelled")
        )

    def action_revision_approve(self):
        # The Manager may approve only before the หนังสือ is sent (ADR-0014).
        if self._sarabun_circulating_document():
            raise UserError(_("หนังสือขออนุมัติปรับแผนกำลังเวียน รอผลจากหนังสือ"))
        res = super().action_revision_approve()
        self._abandon_stale_sarabun_documents()
        return res

    def action_revision_return(self, reason):
        if self._sarabun_circulating_document():
            raise UserError(_("หนังสือขออนุมัติปรับแผนกำลังเวียน รอผลจากหนังสือ"))
        res = super().action_revision_return(reason)
        self._abandon_stale_sarabun_documents()
        return res

    # -- Sarabun outcome → draft state --------------------------------------
    def _on_sarabun_circulating(self, document):
        if self.revision_of_id and self.state == "returned":
            # Re-sent after ตีกลับ/ดึงกลับ: the edited draft passes the checks again.
            self._revision_check()
        return super()._on_sarabun_circulating(document)

    def _on_sarabun_completed(self, document):
        if not self.revision_of_id:
            return super()._on_sarabun_completed(document)
        try:
            return super()._on_sarabun_completed(document)
        except UserError as error:
            raise UserError(
                _("%s\nกรุณาดึงกลับหนังสือ แล้วแก้ไขร่างปรับแผนก่อนส่งใหม่") % error.args[0]
            ) from error

    def _on_sarabun_cancelled(self, document):
        # ยกเลิกการส่ง: the draft stays รออนุมัติปรับแผน, ready for a fresh หนังสือ.
        res = super()._on_sarabun_cancelled(document)
        if self.revision_of_id:
            self.state = "sent"
        return res
