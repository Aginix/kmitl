# -*- coding: utf-8 -*-
from odoo import fields, models


class SarabunRouteTemplate(models.Model):
    _name = "sarabun.route.template"
    _description = "Sarabun Route Template"
    _order = "name"

    name = fields.Char(
        string="Template Name",
        required=True,
    )
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        help="If set, this template is specific to this department",
    )
    line_ids = fields.One2many(
        comodel_name="sarabun.route.template.line",
        inverse_name="template_id",
        string="Route Steps",
        copy=True,
    )


class SarabunRouteTemplateLine(models.Model):
    _name = "sarabun.route.template.line"
    _description = "Sarabun Route Template Line"
    _order = "sequence, id"

    template_id = fields.Many2one(
        comodel_name="sarabun.route.template",
        string="Template",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    routing_type = fields.Selection(
        selection=[
            ("acknowledge", "For Acknowledgement"),
            ("approve", "For Approval"),
        ],
        string="Routing Type",
        required=True,
        default="acknowledge",
    )
    recipient_type = fields.Selection(
        selection=[
            ("user", "User"),
            ("department", "Department"),
            ("role", "Role/Position"),
        ],
        string="Recipient Type",
        required=True,
        default="user",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
    )
    role_id = fields.Many2one(
        comodel_name="sarabun.role",
        string="Role/Position",
        help="Select a role/position for routing",
    )
