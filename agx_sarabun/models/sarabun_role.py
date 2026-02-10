# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class SarabunRole(models.Model):
    """
    Organizational roles/positions for document routing.
    Examples: อธิการบดี, รองอธิการบดี, คณบดี, หัวหน้าภาควิชา, etc.
    """

    _name = "sarabun.role"
    _description = "Sarabun Role/Position"
    _order = "sequence, name"

    name = fields.Char(
        string="Role Name",
        required=True,
        translate=True,
        help="e.g., อธิการบดี, รองอธิการบดี, คณบดี",
    )
    code = fields.Char(
        string="Code",
        help="Short code for the role",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(
        string="Description",
        translate=True,
    )

    # Role category - executive vs academic
    role_category = fields.Selection(
        selection=[
            ("executive", "Executive Position"),
            ("academic", "Academic Position"),
        ],
        string="Category",
        default="executive",
        help="Executive: Administrative positions (e.g., คณบดี, หัวหน้าภาค). "
        "Academic: Academic titles (e.g., ศาสตราจารย์, รองศาสตราจารย์).",
    )

    # Role type for special handling
    role_type = fields.Selection(
        selection=[
            ("static", "Static User"),
            ("dynamic", "Dynamic (Based on Document)"),
        ],
        string="Role Type",
        default="static",
        required=True,
        help="Static: Always routes to assigned user(s). "
        "Dynamic: Determined based on document context (e.g., sender's manager).",
    )

    # For static roles - assigned users
    user_ids = fields.Many2many(
        comodel_name="res.users",
        relation="sarabun_role_user_rel",
        column1="role_id",
        column2="user_id",
        string="Assigned Users",
        help="Users who hold this role. Leave empty for dynamic roles.",
    )

    # For dynamic roles - computation method
    dynamic_method = fields.Selection(
        selection=[
            ("sender_manager", "Sender's Manager"),
            ("dept_head", "Department Head"),
            ("parent_dept_head", "Parent Department Head"),
        ],
        string="Dynamic Method",
        help="How to determine the user for this role based on document context.",
    )

    # Department scope (optional)
    department_ids = fields.Many2many(
        comodel_name="hr.department",
        relation="sarabun_role_department_rel",
        column1="role_id",
        column2="department_id",
        string="Departments",
        help="If set, this role is only available for these departments.",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Role code must be unique!"),
    ]

    def get_users_for_document(self, document):
        """
        Get user(s) for this role based on document context.
        Returns a recordset of res.users.
        """
        self.ensure_one()

        if self.role_type == "static":
            return self.user_ids

        # Dynamic role - compute based on method
        if self.dynamic_method == "sender_manager":
            user = document.sender_user_id
            if user.employee_id and user.employee_id.parent_id:
                return user.employee_id.parent_id.user_id
        elif self.dynamic_method == "dept_head":
            dept = document.sender_department_id
            if dept and dept.manager_id:
                return dept.manager_id.user_id
        elif self.dynamic_method == "parent_dept_head":
            dept = document.sender_department_id
            if dept and dept.parent_id and dept.parent_id.manager_id:
                return dept.parent_id.manager_id.user_id

        return self.env["res.users"]

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.code:
                name = f"[{record.code}] {name}"
            result.append((record.id, name))
        return result

    @api.model
    def get_user_roles(self, user=None):
        """
        Get all roles this user can sign as.
        Returns a recordset of sarabun.role.
        """
        user = user or self.env.user
        return self.search([("user_ids", "in", user.id), ("active", "=", True)])
