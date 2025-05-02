# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectObjectives(models.Model):
    _name = "project.objectives"
    _description = "ProjectObjectives"

    name = fields.Char(string="ชื่อ")
    project_kmitl_id = fields.Many2one("project.kmitl", string="โครงการ")
