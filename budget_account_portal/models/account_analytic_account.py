# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    hierarchy_level = fields.Integer(
        string="Level",
        compute="_compute_hierarchy_level",
        store=False,
        recursive=True,
    )

    @api.depends("parent_id.hierarchy_level")
    def _compute_hierarchy_level(self):
        for record in self:
            if record.parent_id:
                record.hierarchy_level = record.parent_id.hierarchy_level + 1
            else:
                record.hierarchy_level = 0

    @api.model
    def get_as_flat_list(self, plan_id):
        domain = [('plan_id', '=', plan_id), ('parent_id', '=', False)]
        roots = self.search(domain, order="code")

        def flatten_node(node):
            result = [node]
            for child in node.child_ids:
                result.extend(flatten_node(child))
            return result

        flat_list = []
        for node in roots:
            flat_list.extend(flatten_node(node))

        def sort_key(node):
            priority_codes = ['00', '09', '06']
            # Extract first 2 digits of code for priority sorting
            code_prefix = node.code[:2] if len(node.code) >= 2 else node.code

            if code_prefix in priority_codes:
                # Return tuple with priority index first, then code
                return (priority_codes.index(code_prefix), node.code)
            else:
                # Non-priority codes come after priority ones, sorted by code
                return (len(priority_codes), node.code)

        if plan_id == self.env.ref('account_analytic_kmitl.analytic_plan_activities').id:
            return sorted(flat_list, key=sort_key)

        return flat_list
