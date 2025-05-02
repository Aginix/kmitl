# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectImpact(models.Model):
    _name = "project.impact"
    _description = "ProjectImpact"

    name = fields.Char(string="ชื่อ")
