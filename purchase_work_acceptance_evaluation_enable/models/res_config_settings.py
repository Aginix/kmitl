# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResConfigSettings(models.Model):
    _inherit = 'res.config.settings'

    group_enable_eval_on_wa = fields.Boolean(
        string="Enable Evaluation on Work Acceptance",
        implied_group="purchase_work_acceptance_evaluation.group_enable_eval_on_wa",
        default=True,
        readonly=True,
    )
