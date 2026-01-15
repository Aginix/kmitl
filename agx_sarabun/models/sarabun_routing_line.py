# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SarabunRoutingLine(models.Model):
    """
    Route definition - defines WHO should receive the document.
    This is just a "plan" or "template" for routing - no state tracking.
    State tracking is done in sarabun.document.recipient.
    """

    _name = "sarabun.routing.line"
    _description = "Sarabun Routing Line"
    _order = "sequence, id"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    # === Routing Type ===
    routing_type = fields.Selection(
        selection=[
            ("acknowledge", "For Acknowledgement"),
            ("approve", "For Approval"),
        ],
        string="Routing Type",
        required=True,
        default="acknowledge",
    )

    # === Recipient ===
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
        string="Department (System)",
        help="Link to department in system for notification routing",
    )
    department_text = fields.Char(
        string="Department",
        help="Free text for recipient department. Use lookup button to search from system.",
    )
    role_id = fields.Many2one(
        comodel_name="sarabun.role",
        string="Role/Position",
        help="Select a role/position for routing",
    )
    recipient_name = fields.Char(
        string="Recipient",
        compute="_compute_recipient_name",
        store=True,
    )

    # === Computed Fields ===
    @api.depends("recipient_type", "user_id", "department_id", "department_text", "role_id")
    def _compute_recipient_name(self):
        for record in self:
            if record.recipient_type == "user" and record.user_id:
                record.recipient_name = record.user_id.name
            elif record.recipient_type == "department":
                # Prefer department_text for display, fall back to department_id.name
                record.recipient_name = record.department_text or (
                    record.department_id.name if record.department_id else False
                )
            elif record.recipient_type == "role" and record.role_id:
                record.recipient_name = record.role_id.name
            else:
                record.recipient_name = False

    @api.onchange("department_id")
    def _onchange_department_id(self):
        """When department is selected, populate department_text"""
        if self.department_id and not self.department_text:
            self.department_text = self.department_id.name

    # === Constraints ===
    @api.constrains("recipient_type", "user_id", "department_id", "department_text", "role_id")
    def _check_recipient(self):
        for record in self:
            if record.recipient_type == "user" and not record.user_id:
                raise UserError(_("Please select a user for user-type recipient."))
            if record.recipient_type == "department":
                # Must have either department_id (for routing) or department_text (for display)
                if not record.department_id and not record.department_text:
                    raise UserError(
                        _("Please enter department text or select a department for routing.")
                    )
            if record.recipient_type == "role" and not record.role_id:
                raise UserError(_("Please select a role/position for role-type recipient."))
