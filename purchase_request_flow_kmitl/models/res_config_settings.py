from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pa_auto_creator_id = fields.Many2one(
        related="company_id.pa_auto_creator_id",
        readonly=False,
    )
