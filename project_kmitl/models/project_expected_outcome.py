# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectExpectedOutcome(models.Model):
    _name = _description = 'project.expected.outcome'
    _order = "sequence asc, id asc"

    name = fields.Char('ชื่อ', required=True)
    sequence = fields.Integer(index=True, default=1)
    project_id = fields.Many2one(comodel_name="project.project", required=True)
