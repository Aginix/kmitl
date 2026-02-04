# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectMethodology(models.Model):
    _name = 'project.methodology'
    _description = 'ProjectMethodology'

    name = fields.Char('Name')
