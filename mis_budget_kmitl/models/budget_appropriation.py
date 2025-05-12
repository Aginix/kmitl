# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAppropriation(models.Model):
    _inherit = 'budget.appropriation'

    def generate_report(self):
        self.env["mis.report.kmitl.f5"]._generate_report(self.id)
