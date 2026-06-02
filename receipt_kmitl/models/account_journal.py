# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_receipt_kmitl_journal = fields.Boolean(
        string="KMITL Receipt Journal",
        help="When enabled, this journal can be selected on KMITL Receipt documents. "
             "Typically used for cash/bank journals that receive incoming payments.",
    )
