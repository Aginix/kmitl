# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SarabunDocument(models.Model):
    _name= 'sarabun.document'
    _inherit = ['sarabun.document', 'thai.date.mixin']
