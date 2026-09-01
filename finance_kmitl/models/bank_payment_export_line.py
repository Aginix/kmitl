# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class BankPaymentExportLine(models.Model):
    _inherit = "bank.payment.export.line"

    # -------------------------------------------------------------------------
    # Domain override: accept submitted payments
    # -------------------------------------------------------------------------
    @api.model
    def _domain_payment_id(self):
        """Only KMITL transfer vouchers awaiting the bank are selectable.

        Overrides the base domain three times over: it keys off the finance
        office's own status (a KMITL file carries vouchers confirmed for the bank,
        long before the accounting office posts them), off the KMITL เงินโอน method
        instead of Odoo's stock Manual one so cheque and cash payments never end up
        in an e-payment file, and narrows to the file's own paying account — one
        file debits one account, so mixing two is prevented while picking rather
        than rejected afterwards.
        """
        method_transfer_out = self.env.ref(
            "account_kmitl.payment_method_transfer_out",
            raise_if_not_found=False,
        )
        if not method_transfer_out:
            return "[('id', '=', 0)]"
        domain = (
            "[('export_status', '=', 'draft'), "
            "('finance_state', '=', 'confirmed'), "
            "('payment_method_id', '=', %s), "
            "('payment_method_line_id', '=', parent.paying_account_id), "
            "('journal_id.type', '=', 'bank'), "
            "('company_id', '=', company_id), "
            "('currency_id', '=', currency_id)]" % (method_transfer_out.id)
        )
        return domain

    # -------------------------------------------------------------------------
    # The payee's bank account belongs to the voucher, not to the row
    # -------------------------------------------------------------------------
    payment_partner_bank_id = fields.Many2one(
        inverse="_inverse_payment_partner_bank_id",
        # Pinned, because Odoo turns a computed field writable the moment an
        # inverse is given (fields.py ``readonly = not inverse``) and that would
        # silently discard the base's ``states``, leaving the column editable in
        # every state including a file already at the bank. write() calls the
        # inverse regardless of this flag, so nothing is lost by keeping it.
        readonly=True,
        help="The payee account the bank is told to credit. The same one the "
        "voucher carries — correcting it here corrects the voucher, so the file "
        "can never instruct something the voucher does not say.",
    )

    @api.depends("payment_id", "payment_id.partner_bank_id")
    def _compute_payment_default(self):
        """Follow the voucher's payee account instead of copying it once.

        The base takes a snapshot when the row is created, and the row is editable,
        so the two could disagree — and it is the row that is written into the file
        (``_get_receiver_information``). A file may not instruct a bank to credit an
        account the voucher does not name; the money side is one fact, wherever it
        is read from. Adding the voucher's field to the dependencies is what keeps
        the row following it; ``_inverse_payment_partner_bank_id`` keeps the voucher
        following the row.
        """
        return super()._compute_payment_default()

    def _inverse_payment_partner_bank_id(self):
        """Push a correction made on the row back onto the voucher."""
        for line in self:
            payment = line.payment_id
            if payment and payment.partner_bank_id != line.payment_partner_bank_id:
                payment.partner_bank_id = line.payment_partner_bank_id

    # Both paths are declared: overriding the compute replaces the base
    # decorator, so the journal dependency has to be carried over or the
    # fallback would never recompute.
    @api.depends(
        "payment_id.payment_method_line_id.bank_account_id",
        "payment_id.journal_id.bank_account_id",
    )
    def _compute_sending_account(self):
        """Take the sending account from the paying account (หัวจ่าย).

        The base reads the payment journal's bank account, which is always empty
        here: a KMITL journal is a voucher type (ใบสำคัญ) and holds no bank, so
        every generated file went out with a blank "Sending A/C". Falls back to
        the journal so a payment made outside this flow behaves as before.
        """
        res = super()._compute_sending_account()
        for line in self:
            bank_account = line.payment_id.payment_method_line_id.bank_account_id
            if bank_account:
                line.sending_bank_id = bank_account.bank_id
                line.sending_acc_number = bank_account.acc_number
        return res

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
