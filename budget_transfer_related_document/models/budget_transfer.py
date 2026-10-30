from odoo import _, models
from odoo.exceptions import UserError


class BudgetTransfer(models.Model):
    # On the transfer, not on the budget.move it delegates to.
    _inherit = ["budget.transfer", "related.document.mixin"]
    _name = "budget.transfer"

    def _related_document_check_change(self, rows, operation):
        """Cited documents change until the transfer is posted or cancelled,
        as on the form."""
        super()._related_document_check_change(rows, operation)
        if self.state in ("posted", "cancelled"):
            raise UserError(_("แก้ไขเอกสารอ้างอิงไม่ได้ในสถานะปัจจุบัน"))
