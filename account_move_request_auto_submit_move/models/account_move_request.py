# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMoveRequest(models.Model):
    _inherit = "account.move.request"

    def action_validate(self):
        """Override to auto-create and auto-submit bill on validation"""
        # Call parent method to validate the request
        result = super().action_validate()

        # Auto-create and submit bill for each validated request
        for record in self:
            # Skip if bill already exists
            if record.bill_id:
                _logger.info(
                    "Skipping bill creation for move request %s - bill already exists (ID: %s)",
                    record.name,
                    record.bill_id.id,
                )
                continue

            try:
                # Create the bill
                bill_action = record.action_create_bill()

                # Extract the created bill and auto-submit it
                if bill_action and bill_action.get("res_id"):
                    bill_id = bill_action["res_id"]
                    bill = self.env["account.move"].browse(bill_id)

                    if bill.exists() and bill.state == "draft":
                        bill.action_submit()
                        _logger.info(
                            "Auto-created and submitted bill %s (ID: %s) from move request %s",
                            bill.name,
                            bill.id,
                            record.name,
                        )
                    else:
                        _logger.warning(
                            "Bill %s (ID: %s) created but not in draft state: %s",
                            bill.name if bill.exists() else "Unknown",
                            bill_id,
                            bill.state if bill.exists() else "Not found",
                        )

            except Exception as e:
                _logger.error(
                    "Failed to auto-create/submit bill for move request %s: %s",
                    record.name,
                    str(e),
                )
                # Continue processing other records even if one fails

        return result
