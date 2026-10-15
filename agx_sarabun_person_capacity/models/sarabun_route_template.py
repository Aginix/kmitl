# -*- coding: utf-8 -*-
"""Mirror the routing-step reset rules onto the template-line so a template
authored with Person + capacity seeds a step with the capacity intact (and the
template editor sees the same clearing behaviour as the live route form)."""
from odoo import api, models


class SarabunRouteTemplateLine(models.Model):
    _inherit = "sarabun.route.template.line"

    @api.onchange("target_mode")
    def _onchange_target_mode_reset_targets(self):
        self.position_id = False
        self.employee_id = False
        self.department_id = False

    @api.onchange("employee_id")
    def _onchange_employee_clear_capacity(self):
        if self.target_mode != "person":
            return
        self.position_id = False
