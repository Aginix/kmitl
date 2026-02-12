# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptanceLine(models.Model):
    _inherit = 'work.acceptance.line'

    approval_line_id = fields.Many2one(
        'purchase.request.approval.line',
        string='Purchase Request Approval Line',
        ondelete="set null",
        index=True,
        readonly=False,
    )
