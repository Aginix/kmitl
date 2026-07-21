# -*- coding: utf-8 -*-
"""sarabun.addressee.prefix — the salutation (คำขึ้นต้น) that opens the เรียน line.

Today only "เรียน" is used, but the หนังสือ tradition has several openings keyed to
the recipient's rank — กราบทูล, กราบเรียน, เสนอ, ยื่นต่อ … — so the prefix is
configurable master data rather than a hard-coded label.
"""
from odoo import fields, models


class SarabunAddresseePrefix(models.Model):
    _name = "sarabun.addressee.prefix"
    _description = "Sarabun Addressee Prefix (คำขึ้นต้น)"
    _order = "sequence, id"

    name = fields.Char(string="คำขึ้นต้น (Prefix)", required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
