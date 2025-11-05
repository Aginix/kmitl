# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMoveRequest(models.Model):
    _inherit = "account.move.request"

    def action_validate(self):
        """Override to auto-create and auto-submit bill on validation"""
        # Call parent method to validate the request
        result = super().action_validate()

        # Auto-create and submit bill for each validated request
        for record in self:
            bill = record._create_bill()
            bill.action_submit()

        return result
