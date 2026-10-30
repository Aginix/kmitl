from odoo import _, models
from odoo.exceptions import UserError


class BudgetSupportRequest(models.Model):
    _inherit = ["budget.support.request", "related.document.mixin"]
    _name = "budget.support.request"

    def _related_document_check_change(self, rows, operation):
        """Cited documents change while the request itself is editable:
        in draft, and by the named Buddy while it waits for their check."""
        super()._related_document_check_change(rows, operation)
        if not self.can_edit:
            raise UserError(_("แก้ไขเอกสารอ้างอิงไม่ได้ในสถานะปัจจุบัน"))
