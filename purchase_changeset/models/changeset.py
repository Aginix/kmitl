# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class Changeset(models.Model):
    _name = 'changeset'
    _description = 'Changeset'

    name = fields.Char('ชื่อเรื่อง')

