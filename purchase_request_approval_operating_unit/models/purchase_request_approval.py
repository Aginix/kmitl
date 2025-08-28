# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApproval(models.Model):
    _inherit = 'purchase.request.approval'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: self.env["res.users"]._get_default_operating_unit(
            self._uid
        ),
    )
