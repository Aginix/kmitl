# -*- coding: utf-8 -*-
import logging

from odoo import models, fields, api, _
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

        return flat_list
