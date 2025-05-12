# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetTemplate(models.Model):
    _inherit = "budget.template"

    def generate_report(self):
        self.env["mis.report.kmitl.f3_p_003_overall"]._generate_mis_report_template(self.id)
