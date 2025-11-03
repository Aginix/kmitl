# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    evaluation_result_ids = fields.One2many(
        groups="purchase_work_acceptance_evaluation.group_enable_eval_on_wa"
    )
