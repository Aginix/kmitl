# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectGlobalIndex(models.Model):
    _name = _description = 'project.global.index'

    name = fields.Char('ชื่อ')
