# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ProjectStrategicPlan(models.Model):
    _name = _description = "project.strategic.plan"
    _inherit = ["mail.thread"]
    _order = "hierarchy_level asc, code asc"
    _parent_store = True

    name = fields.Char(string="ชื่อแผนยุทธศาสตร์", required=True, tracking=True)
    code = fields.Char(string="รหัสอ้างอิง", required=True, tracking=True)
    level = fields.Integer(string="ระดับแผน", required=True, tracking=True)
    hierarchy_level = fields.Integer(
        string="Level",
        compute='_compute_hierarchy_level',
        store=True,
        readonly=False,
        recursive=True,
        required=True,
        precompute=True,
    )
    parent_path = fields.Char(index=True, unaccent=False)

    parent_id = fields.Many2one(
        "project.strategic.plan",
        string="แผนยุทธศาสตร์หลัก",
        ondelete="cascade",
        index=True,
        tracking=True,
    )

    child_ids = fields.One2many(
        "project.strategic.plan", "parent_id", string="แผนยุทธศาสตร์ย่อย"
    )

    note = fields.Text("Internal Notes", tracking=True)

    children_count = fields.Integer(
        "Children Accounts Count",
        compute="_compute_children_count",
    )

    deprecated = fields.Boolean(
        default=False,
        tracking=True,
        help="Set deprecated to true to mark the project strategic plan that has been outdated, that you should no longer use it.",
    )

    active = fields.Boolean(
        default=True,
        tracking=True,
        help="Set active to false to hide the project strategic plan without removing it.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )

    _sql_constraints = [
        (
            "unique_project_strategic_plan",
            "unique (code)",
            _("Project strategic plan's code must be unique"),
        )
    ]

    @api.depends("child_ids")
    def _compute_children_count(self):
        for record in self:
            record.children_count = len(record.child_ids)

    @api.depends("parent_id.hierarchy_level")
    def _compute_hierarchy_level(self):
        for record in self:
            if record.parent_id:
                record.hierarchy_level = record.parent_id.hierarchy_level + 1
            else:
                record.hierarchy_level = 0

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(
                _("You cannot create recursive project strategic plan.")
            )

    def action_view_children_accounts(self):
        result = {
            "type": "ir.actions.act_window",
            "res_model": "kmitl.project",
            "domain": [("parent_id", "=", self.id)],
            "context": {"default_parent_id": self.id},
            "name": _("Strategic subplans"),
            "view_mode": "list,form",
        }
        return result
