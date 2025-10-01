# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    asset_number = fields.Char(
        string="Asset Number"
    )

    parent_asset = fields.Boolean(
        string="Create Parent Asset",
        help="ถ้าติ๊กถูกเมื่อลงทะเบียนครุภัณฑ์ จะสร้าง parent asset"
    )