# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectFight(models.Model):
    _name = "project.fight"
    _description = "ProjectFight"

    name = fields.Char(string="ชื่อ")
    name_th = fields.Char(string="ชื่อภาษาไทย")
