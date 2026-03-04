# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectOutput(models.Model):
    _name = 'project.output'
    _description = 'ProjectOutput'

    sequence = fields.Integer(index=True, default=1)
    name = fields.Char("Name", required=True)
    line_type = fields.Selection(
        [
            ("output", "Output"),
            ("outcome", "Outcome"),
        ],
        required=True,
    )
    project_id = fields.Many2one(comodel_name="kmitl.project", required=True)
    unit = fields.Char(required=True)
    amount = fields.Float(required=True)

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Amount must be greather than zero"))
