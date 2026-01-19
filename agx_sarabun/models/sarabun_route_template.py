# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class SarabunRouteTemplate(models.Model):
    _name = "sarabun.route.template"
    _description = "Sarabun Route Template"
    _order = "sequence, name"

    name = fields.Char(
        string="Template Name",
        required=True,
    )
    active = fields.Boolean(default=True)
    description = fields.Text(string="Description")
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Priority for matching (lower = higher priority)",
    )

    # === Scope Fields ===
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        help="If set, this template is specific to this department",
    )
    document_type_id = fields.Many2one(
        comodel_name="sarabun.document.type",
        string="Document Type",
        help="If set, this template is specific to this document type",
    )
    origin_model = fields.Char(
        string="Origin Model",
        help="Technical model name (e.g., purchase.request). If set, this template only applies to documents created from this model.",
    )

    # === Condition ===
    condition_domain = fields.Text(
        string="Condition Domain",
        help="Domain to evaluate against origin record. E.g., [('amount_total', '>=', 100000)]. Leave empty to match all.",
    )

    # === Route Steps ===
    line_ids = fields.One2many(
        comodel_name="sarabun.route.template.line",
        inverse_name="template_id",
        string="Route Steps",
        copy=True,
    )

    def match_origin_record(self, origin_record):
        """Check if this template matches the origin record based on condition_domain"""
        self.ensure_one()
        if not self.condition_domain:
            return True  # No condition = always match

        try:
            domain = safe_eval(self.condition_domain, {"uid": self.env.uid})
            return bool(origin_record.filtered_domain(domain))
        except Exception:
            return False  # Invalid domain = no match

    @api.model
    def find_matching_templates(self, origin_record=False, department_id=False, document_type_id=False):
        """Find all templates that match the given criteria"""
        domain = [("active", "=", True)]

        # Build domain with OR conditions for optional scope fields
        if origin_record:
            domain += [
                "|",
                ("origin_model", "=", False),
                ("origin_model", "=", origin_record._name),
            ]

        if department_id:
            domain += [
                "|",
                ("department_id", "=", False),
                ("department_id", "=", department_id),
            ]

        if document_type_id:
            domain += [
                "|",
                ("document_type_id", "=", False),
                ("document_type_id", "=", document_type_id),
            ]

        templates = self.search(domain, order="sequence, name")

        # Filter by condition_domain if origin_record is provided
        if origin_record:
            templates = templates.filtered(lambda t: t.match_origin_record(origin_record))

        return templates


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
