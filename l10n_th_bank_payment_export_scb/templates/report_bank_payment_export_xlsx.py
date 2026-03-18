# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class BankPaymentExportXslx(models.AbstractModel):
    _inherit = "report.bank.payment.export.xlsx"

    def _get_header_data_list(self, obj):
        header_data_list = super()._get_header_data_list(obj)
        if obj.bank == "SICOTHBK":
            header_data_list.extend(
                [
                    (
                        "Product Code",
                        dict(obj._fields["scb_product_code"].selection).get(
                            obj.scb_product_code
                        )
                        or "-",
                    ),
                    ("Effective Date", obj.effective_date.strftime("%d/%m/%Y")),
                ]
            )
        return header_data_list
