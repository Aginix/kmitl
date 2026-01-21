from odoo import Command, models


class AccountMoveRequest(models.Model):
    _inherit = "account.move.request"

    def _create_bill(self):
        """Override to add WHT to invoice lines"""
        self.ensure_one()
        bill = super()._create_bill()

        # Update invoice lines with WHT from request lines
        for request_line, invoice_line in zip(self.line_ids, bill.invoice_line_ids):
            if request_line.wht_tax_id:
                invoice_line.wht_tax_id = request_line.wht_tax_id

        return bill
