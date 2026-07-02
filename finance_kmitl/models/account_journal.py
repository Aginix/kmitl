# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    cheque_layout_id = fields.Many2one(
        comodel_name="cheque.layout",
        string="Cheque Layout",
        help="Print calibration used when printing cheques drawn on this "
        "journal (cheque book).",
    )
