# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectFight(models.Model):
    _name = 'project.fight'
    _description = 'ProjectFight'

    name = fields.Char(string="ชื่อ")
    name_th = fields.Char(string="ชื่อภาษาไทย")
