# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ReceiptRemittance(models.Model):
    _inherit = "kmitl.receipt.remittance"

    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"].operating_unit_default_get(),
    )
