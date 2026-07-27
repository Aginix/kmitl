# Copyright 2024 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BankPaymentTemplate(models.Model):
    _inherit = "bank.payment.template"

    bank = fields.Selection(
        selection_add=[("KASITHBK", "KBANK")],
        ondelete={"KASITHBK": "cascade"},
    )
