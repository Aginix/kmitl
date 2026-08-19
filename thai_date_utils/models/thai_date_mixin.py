# -*- coding: utf-8 -*-
from datetime import datetime

import pytz

from odoo import fields as odoo_fields, models

BANGKOK_TZ = pytz.timezone("Asia/Bangkok")


def to_bangkok(dt):
    """Coerce ``dt`` (a naive-UTC datetime, an ISO string, or a tz-aware datetime) to
    a **fixed Asia/Bangkok** datetime — independent of the user's timezone. Returns
    None if ``dt`` can't be interpreted as a datetime."""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return None
    if not isinstance(dt, datetime):
        return None
    if not dt.tzinfo:
        dt = pytz.utc.localize(dt)  # ORM datetimes are naive UTC
    return dt.astimezone(BANGKOK_TZ)

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
        """Signature date-time — e.g. ``วันที่ 20 ก.ค. 69  เวลา 13:30:31``:
        Arabic numerals, abbreviated month, 2-digit พ.ศ. year, and the time HH:MM:SS in
        a **fixed Asia/Bangkok** timezone (never the user's tz). For the signing date
        on the official document."""
        if not dt:
            return ""
        dt = to_bangkok(dt)
        if not dt:
            return ""
        be_year_2 = (dt.year + 543) % 100
        date_part = "%d %s %02d" % (dt.day, MONTHS_TH_SHORT[dt.month], be_year_2)
        time_part = "%02d:%02d:%02d" % (dt.hour, dt.minute, dt.second)
        return "วันที่ %s  เวลา %s" % (date_part, time_part)
