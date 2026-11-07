from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    advance_clearing_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Advance Clearing Journal",
        domain="[('type', '=', 'general'), ('company_id', '=', id)]",
    )
    advance_clearing_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Advance Receivable Account",
        domain="[('account_type', '=', 'asset_receivable'), ('company_id', '=', id)]",
    )
