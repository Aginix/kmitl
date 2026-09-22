# -*- coding: utf-8 -*-
"""sarabun.standard.comment — reusable เกษียน text as configurable master data.

Actors repeatedly type the same standard phrases when they act on a routing step
(สั่งการ / มอบหมายงาน wording). Admins keep the canned phrases here; the
Act-on-step wizard offers them as a picker that fills its เกษียน comment box, and
a ``sarabun.verb`` may name one as its default so the comment pre-fills on open.

``body`` is plain ``Text`` on purpose: the wizard's target
``sarabun.step.act.wizard.note`` is a ``fields.Text``, so an Html body would
inject markup into a plain-text comment.
"""
from odoo import fields, models


class SarabunStandardComment(models.Model):
    _name = "sarabun.standard.comment"
    _description = "Sarabun Standard Comment (ข้อความมาตรฐาน)"
    _order = "sequence, id"

    name = fields.Char(
        string="ชื่อย่อ (Label)",
        required=True,
        translate=True,
        help="Short label shown in the picker.",
    )
    body = fields.Text(
        string="ข้อความ (Comment text)",
        required=True,
        translate=True,
        help="The เกษียน text written into the comment box when this is picked.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
