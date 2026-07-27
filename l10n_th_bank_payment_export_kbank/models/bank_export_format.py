# Copyright 2024 Aginix Technologies Co., Ltd. (http://aginix.tech)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BankExportFormat(models.Model):
    _inherit = "bank.export.format"

    bank = fields.Selection(
        selection_add=[("KASITHBK", "KBANK")],
        ondelete={"KASITHBK": "cascade"},
    )
