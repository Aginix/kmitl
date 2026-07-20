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

_THAI_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")


def to_thai_digits(value):
    """Convert the ASCII digits in ``value`` to Thai numerals (๐–๙)."""
    return str(value).translate(_THAI_DIGITS)


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

    def format_datetime_thai_sign(self, dt):
        """Signature date-time in Thai — e.g. ``วันที่ ๒๐ ก.ค. ๖๙  เวลา ๑๓:๓๐:๓๑``:
        Thai numerals, abbreviated month, 2-digit พ.ศ. year, and the local-tz time as
        HH:MM:SS. Used for the signing date on the official document."""
        if not dt:
            return ""
        dt = self._coerce_to_datetime(dt) or dt
        if not hasattr(dt, "day"):
            return dt
        be_year_2 = (dt.year + 543) % 100
        date_part = "%d %s %02d" % (dt.day, MONTHS_TH_SHORT[dt.month], be_year_2)
        time_part = "%02d:%02d:%02d" % (dt.hour, dt.minute, dt.second)
        return "วันที่ %s  เวลา %s" % (
            to_thai_digits(date_part), to_thai_digits(time_part)
        )
