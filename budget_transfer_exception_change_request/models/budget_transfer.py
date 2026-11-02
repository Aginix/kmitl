from odoo import models


class BudgetTransfer(models.Model):
    """Bridge: ยืนยันตรวจสอบ waits until no Change request is outstanding.

    The rule only holds while the transfer waits for verification: the
    requester's ยืนยัน after a return goes through with the requests still
    answered, as the Buddy closes them. ``action_verify`` re-runs the rules
    through ``_validate_transfer_data``.
    """

    _inherit = "budget.transfer"

    def budget_transfer_check_outstanding_change_requests(self):
        # base.exception (by_method): return the transfers that FAIL the rule.
        return self.filtered(
            lambda t: t.state == "to_verify" and t._get_outstanding_change_requests()
        )
