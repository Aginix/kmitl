from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_payment_default_return_days = fields.Integer(
        string="Default Return Days",
        config_parameter="advance_payment.default_return_days",
    )
    advance_payment_loan_term = fields.Text(
        string="Loan Term",
        config_parameter="advance_payment.loan_term",
    )
