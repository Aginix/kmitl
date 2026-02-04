# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    account_fiscal_year_id = fields.Many2one(
        comodel_name="account.fiscal.year",
        string="Fiscal year",
        tracking=True,
        states=READONLY_STATES,
    )

    date_planned = fields.Datetime(
        string="Date End"
    )

    # From purchase_order_department
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        states=READONLY_STATES,
        tracking=True
    )

    # From purchase_order_department_operating_unit
    operating_unit_id = fields.Many2one(
        compute="_compute_operating_unit_id",
        default=lambda self: self._default_operating_unit_id(),
        store=True,
    )

    def _default_operating_unit_id(self):
        department_id = self.env.user.employee_id.department_id
        if department_id and department_id.operating_unit_id:
            return department_id.operating_unit_id.id
        return self.env["res.users"].operating_unit_default_get()

    @api.depends("department_id")
    def _compute_operating_unit_id(self):
        for rec in self:
            if rec.department_id and rec.department_id.operating_unit_id:
                rec.operating_unit_id = rec.department_id.operating_unit_id.id
            else:
                rec.operating_unit_id = False