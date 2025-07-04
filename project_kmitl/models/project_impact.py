# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectImpact(models.Model):
    _name = 'project.impact'
    _description = 'ProjectImpact'

    name = fields.Char(string="ชื่อ")
