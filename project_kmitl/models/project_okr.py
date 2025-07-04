# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectOkr(models.Model):
    _name = 'project.okr'
    _description = 'ProjectOkr'

    name = fields.Char(string="ชื่อ")
