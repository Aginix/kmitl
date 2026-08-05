# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    # -------------------------------------------------------------------------
    # Domain override: accept submitted payments
    # -------------------------------------------------------------------------
    @api.model
    def _domain_payment_id(self):
        """Only KMITL transfer payments awaiting the bank are selectable.

        Overrides the base domain twice over: it accepts ``submitted``
        payments (KMITL exports before posting) and keys off the KMITL
        เงินโอน method instead of Odoo's stock Manual one, so cheque and cash
        payments never end up in an e-payment file.
        """
        method_transfer_out = self.env.ref(
            "account_kmitl.payment_method_transfer_out",
            raise_if_not_found=False,
        )
        if not method_transfer_out:
            return "[('id', '=', 0)]"
        domain = (
            "[('export_status', '=', 'draft'), "
            "('state', '=', 'submitted'), "
            "('payment_method_id', '=', %s), "
            "('kmitl_payment_type_id.is_cheque', '=', False), "
            "('journal_id.type', '=', 'bank'), "
            "('company_id', '=', company_id), "
            "('currency_id', '=', currency_id)]"
            % (method_transfer_out.id)
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
    # Sending account (หัวจ่าย) — what the bank file calls "Sending A/C"
    # -------------------------------------------------------------------------
    # The journal is the voucher type (ใบสำคัญ) and carries no bank account, so
    # the sending side comes from the payment's paying account. The base compute
    # (in l10n_th_bank_payment_export_format) keeps the journal's own bank
    # account as the fallback for payments made outside the disbursement flow.
    sending_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        related="payment_id.paying_account_id.bank_account_id",
        string="Sending Account",
        readonly=True,
    )

    @api.depends("payment_id.paying_account_id")
    def _compute_sending_account(self):
        super()._compute_sending_account()
        for line in self:
            bank_account = line.payment_id.paying_account_id.bank_account_id
            if bank_account:
                line.sending_bank_id = bank_account.bank_id
                line.sending_acc_number = bank_account.acc_number

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
