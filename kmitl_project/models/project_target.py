# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectTarget(models.Model):
    _name = _description = "project.target"

    sequence = fields.Integer(index=True, default=1)
    name = fields.Char("Name", required=True)
    line_type = fields.Selection(
        [
            ("target", "Target Group"),
            ("participant", "Participant"),
            ("organizer", "Organizer"),
        ],
        required=True,
    )
    project_id = fields.Many2one(comodel_name="kmitl.project", required=True)
    amount = fields.Integer(required=True)

    @api.constrains("amount")
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_("Amount must be greather than zero"))
