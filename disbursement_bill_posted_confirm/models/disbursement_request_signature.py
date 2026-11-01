# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class DisbursementRequestSignature(models.Model):
    """The bill confirmation as a signature row. The block in ``disbursement``
    loops every row, so declaring the step is all the report needs."""

    _inherit = "disbursement.request.signature"

    step = fields.Selection(
        selection_add=[("bill_confirm", "Accounts Payable Officer")],
        ondelete={"bill_confirm": "cascade"},
    )
