# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    # -------------------------------------------------------------------------
    # Domain override: accept submitted payments
    # -------------------------------------------------------------------------
    @api.model
    def _domain_payment_id(self):
        method_manual_out = self.env.ref("account.account_payment_method_manual_out")
        domain = (
            "[('export_status', '=', 'draft'), "
            "('state', '=', 'submitted'), "
            "('payment_method_id', '=', %s), "
            "('journal_id.type', '=', 'bank'), "
            "('company_id', '=', company_id), "
            "('currency_id', '=', currency_id)]"
            % (method_manual_out.id)
        )
        return domain

    epayment_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="E-Payment Status",
        copy=False,
    )
    epayment_ref = fields.Char(
        string="E-Payment Reference",
        copy=False,
    )
    epayment_date = fields.Datetime(
        string="E-Payment Date",
        copy=False,
    )
    epayment_note = fields.Text(
        string="E-Payment Note",
        copy=False,
    )
