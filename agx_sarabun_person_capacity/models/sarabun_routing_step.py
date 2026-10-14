# -*- coding: utf-8 -*-
"""Person-mode capacity label — clear ``position_id`` when the mode or the pinned
person changes, so the capacity never carries over from a different context.

The core engine already reads ``self.position_id`` as the signing capacity
(``_resolve_capacity`` / ``_signature_snapshot_vals``), so no engine changes are
needed; this add-on only teaches the view surface to surface + clean the value.
"""
from odoo import api, models


class SarabunRoutingStep(models.Model):
    _inherit = "sarabun.routing.step"

    @api.onchange("target_mode")
    def _onchange_target_mode_clear_capacity(self):
        """A Position resolver (position mode) and a capacity label (person mode)
        have different valid sets — a stale value from one mode must not survive
        a switch into the other."""
        if self.is_originator:
            return
        self.position_id = False

    @api.onchange("employee_id")
    def _onchange_employee_clear_capacity(self):
        """In person mode the capacity dropdown is filtered to the pinned person's
        current holdings; a value from the previous person may no longer be valid."""
        if self.target_mode != "person" or self.is_originator:
            return
        self.position_id = False
