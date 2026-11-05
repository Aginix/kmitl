# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectFight(models.Model):
    _name = _description = 'project.fight'

    name = fields.Char('ชื่อ')
    description = fields.Char('คำอธิบาย')

    def name_get(self):
        """Name followed by its description, as in the proposal PDF
        (e.g. Futurist : วิสัยทัศน์กว้างไกล, กล้าแตกต่าง). The form's radio
        widget labels its choices with name_get, without the field context."""
        return [
            (
                rec.id,
                "%s : %s" % (rec.name, rec.description)
                if rec.description
                else rec.name,
            )
            for rec in self
        ]
