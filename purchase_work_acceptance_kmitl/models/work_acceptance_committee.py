# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptanceCommittee(models.Model):
    _inherit = 'work.acceptance.committee'

    approve_role = fields.Selection(
        selection_add=[
            ("secretary", "Secretary"),
        ],
        ondelete={'chairman': 'set default', 'committee': 'set default', 'secretary': 'set default'},
        default="committee",
    )

    mobile_phone = fields.Char(
        related='employee_id.mobile_phone'
    )

    note = fields.Selection(
        selection=[
            ('leave', 'Leave'),
            ('mission', 'Mission'),
        ],
        string='Note',
    )