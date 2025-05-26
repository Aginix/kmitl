# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectOutput(models.Model):
    _name = 'project.output'
    _description = 'ProjectOutput'

    name = fields.Char(string="ชื่อ")
    line_type = fields.Selection(
        [("output", "ผลผลิต"), ("outcome", "ผลลัพธ์")], string="ประเภท"
    )
    unit = fields.Char(string="หน่วยนับ")
    target = fields.Char(string="เป้าหมาย")
    project_kmitl_id = fields.Many2one("project.project", string="โครงการ")
