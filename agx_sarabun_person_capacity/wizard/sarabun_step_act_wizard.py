# -*- coding: utf-8 -*-
"""Act-wizard counterpart — the capacity field is reused for both the Target
Position (position mode) and the signing Capacity (person mode); clear it when
the mode or the pinned person changes so a stale pick never leaks across.

``action_confirm`` already passes ``target_position_id`` through as the step's
``position_id`` regardless of mode (base wizard line ~100), so no override is
needed — the base engine stores the capacity for us.
"""
from odoo import api, models


class SarabunStepActWizard(models.TransientModel):
    _inherit = "sarabun.step.act.wizard"

    @api.onchange("target_mode")
    def _onchange_target_mode_clear_capacity(self):
        self.target_position_id = False

    @api.onchange("target_employee_id")
    def _onchange_employee_clear_capacity(self):
        if self.target_mode != "person":
            return
        self.target_position_id = False
