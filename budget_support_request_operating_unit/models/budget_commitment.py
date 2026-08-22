from odoo import models


class BudgetCommitment(models.Model):
    _inherit = "budget.commitment"

    def _check_beneficiary_reserve_right(self):
        """An approved budget.support.request is itself the authority to
        reserve for another unit (decision-locked: the fulfilling Budget
        Manager should not also need
        ``budget_operating_unit_access_all.group_all_ou_budget``) — as long
        as the beneficiary being set is exactly the request's own unit."""
        authorised = self.filtered(
            lambda commitment: commitment.support_request_id
            and commitment.beneficiary_operating_unit_id
            == commitment.support_request_id.operating_unit_id
        )
        return super(
            BudgetCommitment, self - authorised
        )._check_beneficiary_reserve_right()
