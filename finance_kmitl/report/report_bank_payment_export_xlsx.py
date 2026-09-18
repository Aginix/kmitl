# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class BankPaymentExportXslx(models.AbstractModel):
    _inherit = "report.bank.payment.export.xlsx"

    def _get_header_data_list(self, obj):
        # หัวจ่าย ต่อท้าย Effective Date ที่ล็อคละภูมิของธนาคารเป็นคน append —
        # อยู่ที่นี่รูปแบบเดียวเพราะ finance_kmitl ไม่ได้ depend
        # บนโมดูล KTB/SCB จึง insert ตามชื่อแถว ไม่ตาม MRO. BAY/KBANK ที่ไม่มี
        # แถว Effective Date จะ append ท้าย list แทน
        rows = super()._get_header_data_list(obj)
        paying = obj.paying_account_id
        if not paying:
            return rows
        value = (
            "{} {}".format(
                paying.bank_id.name or "",
                paying.bank_account_id.acc_number or "",
            ).strip()
            or "-"
        )
        entry = ("Paying Account", value)
        for idx, row in enumerate(rows):
            if row and row[0] == "Effective Date":
                rows.insert(idx + 1, entry)
                return rows
        rows.append(entry)
        return rows
