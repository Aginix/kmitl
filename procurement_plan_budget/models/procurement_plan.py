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

    @api.model_create_multi
    def create(self, vals):
        records = super().create(vals)
        ids = records.mapped('id')
        budget_app_lines = self.env['budget.appropriation.line'].search([('procurement_plan_id', 'in', ids)])
        for line in budget_app_lines:
            line.procurement_plan_id._create_pair_with_budget_appropriation(line)
        # for rec in records:
        #     line = self.env['budget.appropriation.line'].search([('procurement_plan_id', '=', rec.id)], limit=1)
        #     if line:

    # def _create_pair_with_budget_appropriation(self):
    #     self.message_post(
    #         body=_(
    #             'Order "%(order_name)s" blocked with reason "%(block_name)s"'
    #         )
    #         % {
    #             "order_name": po.name,
    #             "block_name": po.approval_block_id.name,
    #         }
    #     )
