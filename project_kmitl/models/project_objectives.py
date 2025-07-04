# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectObjectives(models.Model):
    _name = 'project.objectives'
    _description = 'ProjectObjectives'

    name = fields.Char(string="ชื่อ")
    project_kmitl_id = fields.Many2one("project.project", string="โครงการ")
