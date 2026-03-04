# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectImpact(models.Model):
    _name = _description = 'project.impact'

    name = fields.Char('ชื่อ')
