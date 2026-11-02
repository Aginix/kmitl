from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # On res.company: config_parameter= cannot hold a Many2many.
    advance_payment_office_ou_ids = fields.Many2many(
        related="company_id.advance_payment_office_ou_ids",
        readonly=False,
    )
