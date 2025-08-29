# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class WorkAcceptance(models.Model):
    _name = 'work.acceptance'
    _inherit = ['work.acceptance', 'tier.validation']
    _state_from = ["submit"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        res = super(WorkAcceptance, self)._get_under_validation_exceptions()
        res.append("route_id")
        return res

    # still bug
    # def button_submit(self):
    #     res = super().button_submit()
    #     TierDefinition = self.env['tier.definition']
    #     for rec in self:
    #         for user in rec.work_acceptance_committee_ids:
    #             TierDefinition.create({
    #                 'model_id': self.env.ref('purchase_work_acceptance_kmitl.model_work_acceptance').id,
    #                 'name': f'Test Work Acceptance {user.name}',
    #                 'definition_type': 'domain',
    #                 'definition_domain': "[]",
    #                 'review_type': 'individual',
    #                 'reviewer_id': user.employee_id.user_id.id,
    #                 'company_id': rec.company_id.id if rec.company_id else False,
    #             })
    #     return res
