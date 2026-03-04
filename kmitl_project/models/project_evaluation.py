# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectEvaluation(models.Model):
    _name = 'project.evaluation'
    _description = 'ProjectEvaluation'

    name = fields.Char('Name')
