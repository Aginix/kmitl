# -*- coding: utf-8 -*-
"""Act-wizard counterpart — reset all target fields when the mode flips and
clear the capacity when the pinned person changes, so a stale pick never leaks
across modes or people.

``action_confirm`` already passes ``target_position_id`` through as the step's
``position_id`` regardless of mode (base wizard line ~100), so no override is
needed — the base engine stores the capacity for us.
"""
from odoo import api, models


class SarabunStepActWizard(models.TransientModel):
    _inherit = "sarabun.step.act.wizard"

    @api.onchange("target_mode")
    def _onchange_target_mode_reset_targets(self):
        self.target_position_id = False
        self.target_employee_id = False
        self.target_department_id = False

    @api.onchange("target_employee_id")
    def _onchange_employee_clear_capacity(self):
        if self.target_mode != "person":
            return
        self.target_position_id = False
