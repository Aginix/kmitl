from odoo import fields, models


class AccountMoveRequest(models.Model):
    _inherit = "account.move.request"

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal Year",
        tracking=True,
        states={"submitted": [("readonly", True)], "validated": [
            ("readonly", True)], "cancel": [("readonly", True)]},
    )
