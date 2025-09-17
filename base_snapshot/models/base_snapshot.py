# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BaseSnapshot(models.Model):
    _name = 'base.snapshot'
    _description = 'BaseSnapshot'

    name = fields.Char('Name')
