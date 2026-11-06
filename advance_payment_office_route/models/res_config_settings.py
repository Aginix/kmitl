from odoo import fields, models

from .advance_payment import DEFAULT_DIRECTOR_TITLE


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # On res.company: config_parameter= cannot hold a Many2many.
    advance_payment_office_ou_ids = fields.Many2many(
        related="company_id.advance_payment_office_ou_ids",
        readonly=False,
    )
    advance_payment_office_director_title = fields.Char(
        string="ตำแหน่งผู้อำนวยการสำนักงานคลัง (บนสัญญา)",
        config_parameter="advance_payment_office_route.director_title",
        default=DEFAULT_DIRECTOR_TITLE,
    )
