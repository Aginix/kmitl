# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, models


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def restart_validation(self):
        """restart tier with clear data work acceptance committee"""
        if self._name == "work.acceptance":
            self._clear_data_committee()
        return super().restart_validation()

    def _add_comment(self, validate_reject, reviews):
        """Use a localized title for the work acceptance comment dialog."""
        action = super()._add_comment(validate_reject, reviews)
        if self._name == "work.acceptance" and isinstance(action, dict):
            action["name"] = _("Note")
        return action
