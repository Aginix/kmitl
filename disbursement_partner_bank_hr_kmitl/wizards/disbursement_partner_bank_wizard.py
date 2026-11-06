# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class DisbursementPartnerBankWizard(models.TransientModel):
    _inherit = "disbursement.partner.bank.wizard"

    def action_apply(self):
        if self.line_ids.filtered(
            lambda line: line.partner_id.partner_type_id.is_internal
        ):
            raise UserError(
                _(
                    "Staff bank accounts cannot be edited. To add or change one, "
                    "please contact the Human Resources Office."
                )
            )
        return super().action_apply()
