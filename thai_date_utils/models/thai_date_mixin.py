# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import fields as odoo_fields, models

MONTHS_TH = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

MONTHS_TH_SHORT = [
    "", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."
]


class ThaiDateMixin(models.AbstractModel):
    _name = 'thai.date.mixin'
    _description = 'Thai Date Format Utility Mixin'

    def _coerce_to_datetime(self, dt):
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                return None
        if isinstance(dt, datetime) and not dt.tzinfo:
            dt = odoo_fields.Datetime.context_timestamp(self, dt)
        return dt

    def format_date_thai(self, dt):
        if not dt:
            return ""
        dt = self._coerce_to_datetime(dt) or dt
        if not hasattr(dt, "day"):
            return dt
        day = dt.day
        month = MONTHS_TH[dt.month]
        year = dt.year + 543
        return f"{day} {month} พ.ศ. {year}"

    def format_date_thai_short(self, dt):
        """Return e.g. ``1 เม.ย. 2569`` (Buddhist year, abbreviated month)."""
        if not dt:
            return ""
        dt = self._coerce_to_datetime(dt) or dt
        if not hasattr(dt, "day"):
            return dt
        return f"{dt.day} {MONTHS_TH_SHORT[dt.month]} {dt.year + 543}"
