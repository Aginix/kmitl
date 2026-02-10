# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ExpireGroup(models.Model):
    _name = 'expire.group'
    _description = 'ExpireGroup'
    _rec_name = 'name'
    _order = 'min_days'

    name = fields.Char(required=True)
    min_days = fields.Integer(string="Min Days")
    max_days = fields.Integer(string="Max Days")
