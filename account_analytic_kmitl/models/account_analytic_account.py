from odoo import fields, models


class AccountAnalyticAccount(models.Model):
    _inherit = "account.analytic.account"

    related_analytic_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="account_analytic_related_rel",
        column1="src_id",
        column2="dest_id",
        string="Related Analytic Accounts",
    )
