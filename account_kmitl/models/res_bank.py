# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResBank(models.Model):
    """Adds the abbreviation the treasury office actually calls a bank by.

    ``name`` carries the formal Thai/English name and ``bic`` is what the
    e-payment layouts switch on — neither is short enough to use wherever a
    bank needs naming compactly, e.g. a cash-movement route rendered as one
    line (disbursement_cash_movement_kmitl).
    """

    _inherit = "res.bank"

    short_name = fields.Char(
        help="The abbreviation the treasury office uses in everyday speech "
        "(SCB, KTB, BAY, KBANK) — not a formal code, and not read by any bank "
        "file. Used wherever a bank needs naming compactly.",
    )
