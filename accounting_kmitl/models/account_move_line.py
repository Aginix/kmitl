# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    partner_company_type = fields.Selection(
        related="partner_id.company_type",
        store=True,
        index=True,
        string="ประเภทคู่ค้า",
    )
