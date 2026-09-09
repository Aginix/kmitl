# -*- coding: utf-8 -*-
from odoo import _, models, tools


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def _advance_after_reserved(self):
        """A project-funded expense already cleared its own approval upstream
        (จัดโครงการ + ขอใช้เงิน, kmitl_project ADR-0005) — spending the money it
        reserved is just paperwork through the expense module, so skip the
        e-Saraban round entirely and land straight in ``approved`` (see
        agx_approval docs/adr/0005-project-mode-auto-approve-skips-esaraban).
        The request never rests in ``to_send``, so agx_approval_sarabun's
        routing button and submit guard never see it."""
        if self.budget_selection_mode == "project":
            self._track_set_log_message(
                tools.plaintext2html(
                    _("อนุมัติอัตโนมัติ: ใช้งบโครงการที่อนุมัติแล้ว (ข้ามสารบรรณ)")
                )
            )
            self.state = "approved"
            return True
        return super()._advance_after_reserved()
