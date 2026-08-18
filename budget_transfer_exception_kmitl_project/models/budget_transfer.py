from odoo import models


class BudgetTransfer(models.Model):
    """Bridge: align project (``is_project``) transfer lines with ``kmitl.project``.

    The generic comparison lives in ``budget_transfer_exception``; this only wires
    the project spec into the detection method the rule (data) references.
    """

    _inherit = "budget.transfer"

    _KMITL_PROJECT_SPEC = {
        "flag": "account_is_project",
        "tag_field": "kmitl_project_analytic_id",
        "model": "kmitl.project",
        "label": "โครงการ/กิจกรรม",
    }

    def budget_transfer_check_kmitl_project_source(self):
        return self.filtered(
            lambda t: t._transfer_source_mismatches(t._KMITL_PROJECT_SPEC)
        )
