# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models

from .kmitl_student_catalog import DEFAULT_URL


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    kmitl_student_api_url = fields.Char(
        string="Student Catalog URL",
        config_parameter="partner_student_kmitl_api.api_url",
        default=DEFAULT_URL,
    )
    kmitl_student_api_key = fields.Char(
        string="Student Catalog API Key",
        config_parameter="partner_student_kmitl_api.api_key",
    )
