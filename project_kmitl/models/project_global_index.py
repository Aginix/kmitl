# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectGlobalIndex(models.Model):
    _name = 'project.global.index'
    _description = 'ProjectGlobalIndex'

    name = fields.Char(string="ชื่อ")
