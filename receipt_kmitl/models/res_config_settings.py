# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    receipt_kmitl_walkin_partner_id = fields.Many2one(
        "res.partner",
        string="Walk-in Partner",
        config_parameter="receipt_kmitl.walkin_partner_id",
        help="Default partner used on KMITL receipts when no specific "
             "partner is selected.",
    )
