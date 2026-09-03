# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number


class BankPaymentExport(models.Model):
    _inherit = "bank.payment.export"

    bank = fields.Selection(
        selection_add=[("SICOTHBK", "SCB")],
        ondelete={"SICOTHBK": "cascade"},
    )
    scb_company_id = fields.Char(
        string="SCB Company ID",
        size=12,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    # filter
    scb_is_editable = fields.Boolean(
        compute="_compute_scb_editable",
        string="SCB Editable",
    )
    scb_bank_type = fields.Selection(
        selection=[
            ("1", "1 - Next Day"),
            ("2", "2 - Same Day Afternoon"),
        ],
        default="1",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_product_code = fields.Selection(
        selection=[
            ("BNT", "BNT - Bahtnet"),
            ("DCP", "DCP - Direct Credit"),
            ("MCL", "MCL - Media Clearing"),
            ("PAY", "PAY - Payroll"),
            ("PA2", "PA2 - Payroll 2"),
            ("PA3", "PA3 - Payroll 3"),
            ("PA4", "PA4 - MediaClearing Payroll"),
            ("PA5", "PA5 - MediaClearing Payroll 2"),
            ("PA6", "PA6 - MediaClearing Payroll 3"),
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_delivery_mode = fields.Selection(
        selection=[
            ("M", "M - Send by Registered mail"),
            ("C", "C - Send by messenger to Customer"),
            ("P", "P - Receiving pickup at SCB branch"),
            ("S", "S - Send back to SCBBusinessNet"),
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_pickup_location = fields.Selection(
        selection=[
            ("C001", "C001 - รัชโยธิน"),
            ("C002", "C002 - ชิดลม"),
            ("C003", "C003 - มาบตาพุด"),
            ("C004", "C004 - ลาดกระบัง"),
            ("C005", "C005 - ท่าแพ"),
            ("C006", "C006 - อโศก"),
            ("C007", "C007 - พัทยา สาย2"),
            ("C008", "C008 - พระราม 4"),
            ("C009", "C009 - ถนนเชิดวุฒากาศ"),
            ("C010", "C010 - แหลมฉบัง"),
            ("C011", "C011 - ไอทีสแควร์ (หลักสี่)"),
            ("C012", "C012 - สุวรรณภูมิ"),
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_service_type = fields.Selection(
        selection=[
            ("01", "01 - เงินเดือน, ค่าจ้าง, บำเหน็จ, บำนาญ"),
            ("02", "02 - เงินปันผล"),
            ("03", "03 - ดอกเบี้ย"),
            ("04", "04 - ค่าสินค้า, บริการ"),
            ("05", "05 - ขายหลักทรัพย์"),
            ("06", "06 - คืนภาษี"),
            ("07", "07 - เงินกู้"),
            ("59", "59 - อื่น ๆ"),
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_service_type_bahtnet = fields.Selection(
        selection=[
            ("00", "00 - Other"),
            ("01", "01 - Freight"),
            ("02", "02 - Insurance Premium"),
            ("03", "03 - Trasportation Cost"),
            ("04", "04 - Travelling Expenses (Thai)"),
            ("05", "05 - Forign Tourist Expenses"),
            ("06", "06 - Interest Paid"),
            ("07", "07 - Dividened"),
            ("08", "08 - Education"),
            ("09", "09 - Royalty Fee"),
            ("10", "10 - Agency Expenses"),
            ("11", "11 - Advertising Fee"),
            ("12", "12 - Communication Cost"),
            ("13", "13 - Personal Remittance / Family Support"),
            ("14", "14 - Money Transfer for Government"),
            ("15", "15 - Embassy / Military / Government Expenses"),
            ("16", "16 - Thai Lobour Money Transfer"),
            ("17", "17 - Salary"),
            ("18", "18 - Commission Fee"),
            ("19", "19 - Loan"),
            ("20", "20 - Direct Investment"),
            ("21", "21 - Portfolio Investment"),
            ("22", "22 - Trade Transaction"),
            ("23", "23 - Fixed Asset Investment"),
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_invoice_language = fields.Selection(
        selection=[("T", "T - Thai"), ("E", "E - English")],
        ondelete={
            "T": "cascade",
            "E": "cascade",
        },
        default="T",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_is_invoice_present = fields.Boolean(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_is_wht_present = fields.Boolean(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_is_credit_advice = fields.Boolean(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_wht_signatory = fields.Selection(
        selection=[("B", "B - Bank"), ("C", "C - Corporate")],
        ondelete={
            "B": "cascade",
            "C": "cascade",
        },
        default="B",
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_beneficiary_charge = fields.Boolean(
        string="Beneficiary Charge",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_remark = fields.Char(
        string="Remark",
        size=50,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    scb_payment_type_code = fields.Selection(
        selection=[
            ("CSH", "CSH - Cash"),
            ("BCQ", "BCQ - Branch or other bank chqs"),
            ("HCQ", "HCQ - Home chqs"),
            ("DCA", "DCA - Current A/C"),
            ("DSA", "DSA - Saving A/C"),
            ("BCA", "BCA - Current A/C - other branch"),
            ("BSA", "BSA - Saving A/C - other branch"),
            ("FCA", "FCA - Foreign cur. Current A/C"),
            ("FSA", "FSA - Foreign cur. Saving A/C"),
            ("SPD", "SPD - Suspense debtor"),
            ("SPC", "SPC - Suspense creditor"),
            ("UST", "UST - Unsettled"),
            ("OFA", "OFA - Offline Account"),
            ("FWD", "FWD - Forward Value"),
        ],
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.depends("bank")
    def _compute_required_effective_date(self):
        res = super()._compute_required_effective_date()
        for rec in self.filtered(lambda export: export.bank == "SICOTHBK"):
            rec.is_required_effective_date = True
        return res

    @api.depends("bank")
    def _compute_scb_editable(self):
        for export in self:
            export.scb_is_editable = True if export.bank == "SICOTHBK" else False

    def _get_address(self, partner, max_length):
        """Concatenate partner address fields into a single string."""
        parts = [
            partner.street or "",
            partner.street2 or "",
            partner.city or "",
            partner.state_id.name if partner.state_id else "",
            partner.zip or "",
        ]
        return " ".join(p for p in parts if p)[:max_length]

    def _get_wht_income_type(self, wht_line):
        wht_income_type = wht_line.wht_cert_income_type.lower()
        if len(wht_income_type) == 4:
            wht_income_type = "{}.{}".format(wht_income_type[:3], wht_income_type[3:])
        return wht_income_type

    def _get_amount_wht_invoice(self, invoice, line):
        """Return the withholding-tax amount for an invoice in the SCB
        006 invoice-detail sub-record.

        Falls back to any ``amount_wht`` field on the invoice, else 0.0, so
        the export no longer raises ``AttributeError`` when invoice detail is
        present.

        TODO: confirm the WHT source/rounding against the official SCB BCM
        spec and a real sample that contains invoice/WHT detail (the KMITL
        sample has none).
        """
        self.ensure_one()
        return getattr(invoice, "amount_wht", 0.0) or 0.0

    def _get_text_file_prefix(self, text):
        """SCB BCM domestic files start with a 40-character SHA-1 checksum
        line computed over the file body.

        TODO: confirm the exact hash input/boundary against the official SCB
        BCM spec + a full (untrimmed) sample. The KMITL sample is trimmed, so
        this digest could not be reproduced byte-for-byte.
        """
        prefix = super()._get_text_file_prefix(text)
        if self.bank == "SICOTHBK":
            encoding = self.bank_export_format_id.encoding or "utf-8"
            digest = (
                hashlib.sha1(text.encode(encoding, errors="replace"))
                .hexdigest()
                .upper()
            )
            return "{}\r\n".format(digest)
        return prefix

    def _check_constraint_confirm(self):
        res = super()._check_constraint_confirm()
        for rec in self.filtered(lambda export: export.bank == "SICOTHBK"):
            if rec.scb_product_code == "DCP" and any(
                len(sanitize_account_number(line.payment_partner_bank_id.acc_number))
                != 10
                for line in rec.export_line_ids
            ):
                raise UserError(_("Account Number must only be 10 digits."))
        return res

    def _check_constraint_line(self):
        res = super()._check_constraint_line()
        self.ensure_one()
        if self.bank == "SICOTHBK":
            for line in self.export_line_ids:
                if not line.payment_partner_bank_id:
                    raise UserError(
                        _("Recipient Bank with %(payment)s is not selected.")
                        % {
                            "payment": line.payment_id.name,
                        }
                    )
                if line.scb_beneficiary_email and len(line.scb_beneficiary_email) > 64:
                    raise UserError(
                        _(
                            "The length of an email %(payment)s cannot exceed 64 characters."
                        )
                        % {
                            "payment": line.payment_id.name,
                        }
                    )
            # DCP credits SCB accounts and the layout writes 014 itself; every
            # other product reads the code off the payee's bank.
            if self.scb_product_code != "DCP":
                self._check_receiving_bank_code(self.export_line_ids)
        return res
