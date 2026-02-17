# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_request_allow_supplier_state = fields.Boolean(
        string='เปิดใช้งานขั้นตอนการตรวจสอบของเจ้าหน้าที่พัสดุ',
        config_parameter='purchase_request_verification.enable_verification',
        help="เพิ่มขั้นตอนการตรวจสอบของเจ้าหน้าที่พัสดุก่อนเข้าสู่ขั้นตอนของการเงิน",
    )