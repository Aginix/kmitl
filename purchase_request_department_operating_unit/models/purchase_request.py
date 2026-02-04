# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    department_id = fields.Many2one(
        store=True,
        readonly=False
    )

    def _default_operating_unit_id(self):
        department_id = self.env.user.employee_id.department_id
        if department_id and department_id.operating_unit_id:
            return department_id.operating_unit_id.id
        return self.env["res.users"].operating_unit_default_get()

    operating_unit_id = fields.Many2one(
        compute="_compute_operating_unit_id",
        default=lambda self: self._default_operating_unit_id(),
        store=True,
        readonly=False
    )

    @api.depends("department_id")
    def _compute_operating_unit_id(self):
        for rec in self:
            if rec.department_id and rec.department_id.operating_unit_id:
                rec.operating_unit_id = rec.department_id.operating_unit_id.id
            else:
                rec.operating_unit_id = False

    can_edit_operating_unit = fields.Boolean(
        compute="_compute_can_edit_operating_unit",
    )

    def _compute_can_edit_operating_unit(self):
        user_ou_count = len(self.env.user.operating_unit_ids)
        for rec in self:
            rec.can_edit_operating_unit = user_ou_count > 1