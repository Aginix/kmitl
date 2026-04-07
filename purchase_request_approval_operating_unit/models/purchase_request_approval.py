# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    READONLY_STATES = {
        'to_approve': [('readonly', True)],
        'approved': [('readonly', True)],
        'rejected': [('readonly', True)],
    }

    requesting_operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Requesting Operating Unit",
        states=READONLY_STATES,
        default=lambda self: self.env["res.users"].operating_unit_default_get(
            self.env.uid
        ),
    )

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit (OU)",
        states=READONLY_STATES,
        default=lambda self: self.env["res.users"].operating_unit_default_get(
            self.env.uid
        ),
    )
