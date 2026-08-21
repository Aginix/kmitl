# -*- coding: utf-8 -*-
from odoo import models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def _open_actual_on_approval(self):
        """Advance a freshly-approved request straight into actual-expense
        entry (``approved`` → ``actual``).

        Actual expenses have always been recorded in the ``actual`` state; the
        only change here is that the requester no longer clicks "บันทึกค่าใช้จ่าย
        จริง" to get there. ``approved`` becomes a transient checkpoint, so
        everything downstream (billing, disbursement, voucher print) keeps
        keying off ``actual``/``billed`` unchanged.
        """
        self.filtered(lambda r: r.state == "approved").action_record_actual()

    def action_approve(self):
        """Internal-approval fallback: open actual entry right after approval."""
        res = super().action_approve()
        self._open_actual_on_approval()
        return res

    def _on_sarabun_completed(self, document):
        """e-Saraban approval outcome: open actual entry right after approval."""
        res = super()._on_sarabun_completed(document)
        self._open_actual_on_approval()
        return res
