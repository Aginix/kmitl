# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResBank(models.Model):
    """The bank is what decides where the ink lands.

    A cheque form is printed by the bank that issued the book, so every book held
    at one bank shares one layout and no two banks share one. That makes the bank
    the natural place to hang the calibration — not the journal, which is a
    voucher type (ใบสำคัญ) and would have given every bank the same layout, and
    not the individual bank account, which would ask the treasury office to
    calibrate the same printed form once per account.
    """

    _inherit = "res.bank"

    cheque_layout_id = fields.Many2one(
        comodel_name="cheque.layout",
        string="Cheque Layout",
        help="Print calibration for this bank's cheque form. Used when printing "
        "any cheque drawn on a book held here.",
    )
