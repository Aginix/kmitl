# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _get_committee_line(self, purchase_requests=None):
        committees = self.mapped("work_acceptance_committee_ids")
        lines = [(0, 0, self._prepare_committee_line(line)) for line in committees]
        return lines

    def action_view_wa(self):
        result = super().action_view_wa()
        lines = self._get_committee_line()
        result["context"]["default_work_acceptance_committee_ids"] = lines
        result["context"]["default_wa_tier_validation"] = self.wa_tier_validation
        return result