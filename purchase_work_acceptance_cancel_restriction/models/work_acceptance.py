# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'
    _state_from = ["in_review"]
    _state_to = ["accept"]

    state = fields.Selection(
        selection_add = [('in_review', 'In Review'), ('accept',)]
    )

    def _get_under_validation_allowed_fields(self):
        fields = super()._get_under_validation_allowed_fields()
        return fields + ["state"]

    def request_validation(self):
        self.write({"state": "in_review"})
        return super().request_validation()