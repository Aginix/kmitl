# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models

MONTHS_TH = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]


class ThaiDateMixin(models.AbstractModel):
    _name = 'thai.date.mixin'
    _description = 'Thai Date Format Utility Mixin'

    def format_date_thai(self, dt):
        if not dt:
            return ""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                return dt
        day = dt.day
        month = MONTHS_TH[dt.month]
        year = dt.year + 543
        return f"{day} {month} พ.ศ. {year}"
