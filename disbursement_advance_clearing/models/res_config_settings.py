from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_clearing_journal_id = fields.Many2one(
        related="company_id.advance_clearing_journal_id", readonly=False
    )
    advance_clearing_account_id = fields.Many2one(
        related="company_id.advance_clearing_account_id", readonly=False
    )
