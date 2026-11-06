from odoo import fields, models


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    advance_payment_id = fields.Many2one(
        related="payment_id.advance_payment_id",
        string="สัญญายืมเงิน",
    )

    def action_open_advance_payment(self):
        """Open the loan in a new browser tab, keeping the file open."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": "/web#id=%s&model=advance.payment&view_type=form"
            % self.advance_payment_id.id,
            "target": "new",
        }
