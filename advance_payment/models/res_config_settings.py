from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_payment_default_return_days = fields.Integer(
        string="Default Return Days",
        config_parameter="advance_payment.default_return_days",
    )
    advance_payment_loan_term = fields.Char(
        string="Loan Term",
        config_parameter="advance_payment.loan_term",
    )
    advance_payment_receivable_account_id = fields.Many2one(
        "account.account",
        string="Advance Payment Receivable Account",
        config_parameter="advance_payment.receivable_account_id",
    )
