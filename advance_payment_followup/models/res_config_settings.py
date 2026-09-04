# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    advance_payment_followup_notify_days = fields.Integer(
        string="แจ้งเตือนล่วงหน้าก่อนครบกำหนดคืน (วัน)",
        default=7,
        config_parameter="advance_payment_followup.notify_before_days",
    )
