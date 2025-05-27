# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectStrategicPlan(models.Model):
    _name = 'project.strategic.plan'
    _description = 'ProjectStrategicPlan'
    _parent_name = 'parent_id'

    name = fields.Char(string='ชื่อแผนยุทธศาสตร์')
    level = fields.Integer(string='ระดับแผน')
    parent_id = fields.Many2one(
        'project.strategic.plan',
        string='แผนยุทธศาสตร์หลัก',
        ondelete='cascade',
        index=True
    )
    child_ids = fields.One2many(
        'project.strategic.plan',
        'parent_id',
        string='แผนยุทธศาสตร์ย่อย'
    )
