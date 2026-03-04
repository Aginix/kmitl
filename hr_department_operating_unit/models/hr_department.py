# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        string="Operating Unit",
        default=lambda self: (self.env["res.users"].operating_unit_default_get()),
        compute="_compute_operating_unit",
        readonly=False,
        recursive=True,
        store=True
    )

    parent_id = fields.Many2one(
        compute="_compute_operating_unit",
        readonly=False,
        store=True
    )

    @api.constrains('operating_unit_id', 'parent_id')
    def _check_operating_unit_match_parent(self):
        for record in self:
            if record.parent_id and record.operating_unit_id != record.parent_id.operating_unit_id:
                raise ValidationError(
                    "The Operating Unit must match the Operating Unit of the parent department."
                )

    @api.depends('parent_id.operating_unit_id', 'parent_id')
    def _compute_operating_unit(self):
        for record in self:
            if record.parent_id:
                record.operating_unit_id = record.parent_id.operating_unit_id
