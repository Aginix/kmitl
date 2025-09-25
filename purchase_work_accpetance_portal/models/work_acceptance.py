# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

