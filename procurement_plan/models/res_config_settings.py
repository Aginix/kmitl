# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Analytic Accounting
    analytic_plan_id = fields.Many2one(
        comodel_name='account.analytic.plan',
        string="Default Plan",
        readonly=False,
        related='company_id.analytic_plan_id',
    )
