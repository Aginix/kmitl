# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequestApprovalLine(models.Model):
    _inherit = 'purchase.request.approval.line'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        related="approval_id.operating_unit_id",
        string="Operating Unit",
    )
