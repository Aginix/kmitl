# Copyright 2024 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    bank = fields.Selection(
        selection_add=[("KASITHBK", "KBANK")],
        ondelete={"KASITHBK": "cascade"},
    )
    # Configuration
    kbank_company_id = fields.Char(
        string="KBANK Company ID",
        size=6,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    kbank_sender_name = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    kbank_service_type = fields.Selection(
        selection=[
            ("01", "01 - เงินเดือน ค่าจ้าง บำเหน็จ บำนาญ"),
            ("02", "02 - เงินปันผล"),
            ("03", "03 - ดอกเบี้ย"),
            ("04", "04 - ค่าสินค้า บริการ"),
            ("05", "05 - ขายหลักทรัพย์"),
            ("06", "06 - คืนภาษี"),
            ("07", "07 - เงินกู้"),
            ("59", "59 - อื่น ๆ"),
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    # filter
    kbank_is_editable = fields.Boolean(
        compute="_compute_kbank_editable",
        string="KBANK Editable",
    )

    @api.depends("bank")
    def _compute_required_effective_date(self):
        res = super()._compute_required_effective_date()
        for rec in self.filtered(lambda l: l.bank == "KASITHBK"):
            rec.is_required_effective_date = True
        return res

    @api.depends("bank")
    def _compute_kbank_editable(self):
        for export in self:
            export.kbank_is_editable = export.bank == "KASITHBK"

    def _check_constraint_line(self):
        res = super()._check_constraint_line()
        self.ensure_one()
        if self.bank == "KASITHBK":
            for line in self.export_line_ids:
                if not line.payment_partner_bank_id:
                    raise UserError(
                        _("Recipient Bank with %(payment)s is not selected.")
                        % {"payment": line.payment_id.name}
                    )
        return res

    def _check_constraint_confirm(self):
        res = super()._check_constraint_confirm()
        # KBANK K-Cash Connect Plus (direct credit) requires a 10-digit
        # beneficiary account number (same-bank transfer).
        for rec in self.filtered(lambda l: l.bank == "KASITHBK"):
            if any(
                len(sanitize_account_number(line.payment_partner_bank_id.acc_number))
                != 10
                for line in rec.export_line_ids
            ):
                raise UserError(_("Account Number must only be 10 digits."))
        return res
