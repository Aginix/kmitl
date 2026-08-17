from odoo import models


class BudgetTransfer(models.Model):
    """Bridge: align procurement-plan transfer lines with ``procurement.plan``.

    The generic comparison lives in ``budget_transfer_exception``; this only wires
    the procurement-plan spec into the detection method the rule (data) references.
    """

    _inherit = "budget.transfer"

    _PROCUREMENT_PLAN_SPEC = {
        "flag": "account_is_procurement",
        "tag_field": "procurement_plan_analytic_id",
        "model": "procurement.plan",
        "label": "แผนจัดซื้อจัดจ้าง",
    }

    def budget_transfer_check_procurement_plan_source(self):
        return self.filtered(
            lambda t: t._transfer_source_mismatches(t._PROCUREMENT_PLAN_SPEC)
        )
