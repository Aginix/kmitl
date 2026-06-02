# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    receipt_kmitl_walkin_partner_id = fields.Many2one(
        "res.partner",
        string="Walk-in Partner",
        config_parameter="receipt_kmitl.walkin_partner_id",
        help="Default partner used on KMITL receipts when no specific "
             "partner is selected.",
    )
    receipt_kmitl_default_cash_journal_id = fields.Many2one(
        "account.journal",
        string="Default Cash Journal",
        config_parameter="receipt_kmitl.default_cash_journal_id",
        domain="[('is_receipt_kmitl_journal', '=', True), ('type', '=', 'cash')]",
    )
    receipt_kmitl_default_bank_journal_id = fields.Many2one(
        "account.journal",
        string="Default Bank Journal",
        config_parameter="receipt_kmitl.default_bank_journal_id",
        domain="[('is_receipt_kmitl_journal', '=', True), ('type', '=', 'bank')]",
    )
