# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProcurementPlan(models.Model):
    _inherit = 'procurement.plan'

    def _compute_can_edit(self):
        super()._compute_can_edit()
        for rec in self:
            result = self.env['budget.appropriation.line'].search([('procurement_plan_id', '=', rec.id)], limit=1)
            if result:
                rec.can_edit = False

    def _get_record_url(self):
        return "/web#id={}&model={}&view_type=form".format(
            self.id, self._name
        )
