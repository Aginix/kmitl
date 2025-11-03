# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class WorkAcceptance(models.Model):
    _inherit = 'work.acceptance'

    evaluation_result_ids = fields.One2many(
        comodel_name="work.acceptance.evaluation.result",
        inverse_name="wa_id",
        string="Evaluation Results",
        default=lambda self: self._default_evaluation_result_ids(),
        groups="purchase_work_acceptance_evaluation.group_enable_eval_on_wa"
    )
