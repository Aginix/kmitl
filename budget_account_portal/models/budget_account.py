# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BudgetAccount(models.Model):
    _inherit = "budget.account"

    @api.model
    def get_as_flat_list(self, budget_type="expense"):
        domain = [("budget_type", "=", budget_type), ("parent_id", "=", False)]
        roots = self.search(domain, order="code")

        def flatten_node(node):
            result = [node]
            for child in node.child_ids:
                result.extend(flatten_node(child))
            return result

        flat_list = []
        for node in roots:
            flat_list.extend(flatten_node(node))

        return flat_list
