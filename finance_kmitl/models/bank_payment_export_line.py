# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    # -------------------------------------------------------------------------
    # Domain override: accept submitted payments
    # -------------------------------------------------------------------------
    @api.model
    def _domain_payment_id(self):
        method_manual_out = self.env.ref(
            "account.account_payment_method_manual_out",
            raise_if_not_found=False,
        )
        if not method_manual_out:
            return "[('id', '=', 0)]"
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

    # -------------------------------------------------------------------------
    # E-payment result confirmation (manual)
    # -------------------------------------------------------------------------
    def _apply_epayment_result(self, status, ref=None, date=None, note=None):
        """Record the bank result on the export line and propagate it to the
        payment so downstream flows (e.g. the disbursement request) can react.

        A later phase adds a bank-result file import wizard that funnels every
        parsed row through this same choke point.
        """
        for line in self:
            vals = {"epayment_status": status}
            vals["epayment_date"] = date or fields.Datetime.now()
            if ref is not None:
                vals["epayment_ref"] = ref
            if note is not None:
                vals["epayment_note"] = note
            line.write(vals)
            if line.payment_id:
                line.payment_id.bank_result_status = status

    def action_mark_epayment_success(self):
        self._apply_epayment_result("success")

    def action_mark_epayment_failed(self):
        self._apply_epayment_result("failed")
