# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    default_paying_account_id = fields.Many2one(
        comodel_name="kmitl.paying.account",
        string="Default Paying Account",
        help="หัวจ่ายตั้งต้นของสถาบัน — used for a payee whose bank is not one "
        "of the main paying banks. A payment subject may override it, but the "
        "institute-wide rule lives here so it is stated once.",
    )
