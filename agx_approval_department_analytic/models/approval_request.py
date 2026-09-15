from odoo import api, models


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    @api.onchange("department_analytic_id")
    def _onchange_department_analytic_id(self):
        self._update_analytic_distribution("departments")
