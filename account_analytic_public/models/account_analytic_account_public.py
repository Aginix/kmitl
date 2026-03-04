# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAnalyticAccountPublic(models.Model):
    _name = 'account.analytic.account.public'
    _inherit = ['account.analytic.account']
    _description = 'AccountAnalyticAccountPublic'
    _auto = False
    _rec_names_search = ["complete_name", "code"]

    @property
    def _table_query(self):
        return "select * from account_analytic_account"
