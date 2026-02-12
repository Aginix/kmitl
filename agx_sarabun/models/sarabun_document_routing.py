# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

ROUTING_TYPE_SEQUENCE = {
    "acknowledge": 10,
    "approve": 100,
}


class SarabunDocumentRouting(models.Model):
    """
    Routing step definition - defines the type and recipient for each step.
    Resolved users are stored in sarabun.document.routing.user immediately.
    """

    _name = "sarabun.document.routing"
    _description = "Document Routing"
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
        string="Department",
        help="Select department for routing and notifications",
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

    # === Resolved Users ===
    routing_user_ids = fields.One2many(
        comodel_name="sarabun.document.routing.user",
        inverse_name="routing_id",
        string="Resolved Users",
    )
    routing_user_count = fields.Integer(
        string="User Count",
        compute="_compute_routing_user_info",
        store=True,
    )
    routing_user_names = fields.Char(
        string="Resolved Users",
        compute="_compute_routing_user_info",
        store=True,
    )

    # === Status ===
    document_state = fields.Selection(
        related="document_id.state",
        string="Document State",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        compute="_compute_state",
        store=True,
        default="draft",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence'):
                routing_type = vals.get('routing_type')
                vals['sequence'] = ROUTING_TYPE_SEQUENCE.get(routing_type, 10)
        records = super().create(vals_list)
        for record in records:
            record._resolve_users()
        return records

    def write(self, vals):
        for record in self:
            if record.document_id.state != 'draft':
                raise UserError(
                    _("Cannot modify routing after document has been sent.")
                )

        if 'routing_type' in vals and not vals.get('sequence'):
            vals['sequence'] = ROUTING_TYPE_SEQUENCE.get(vals['routing_type'], 10)
        result = super().write(vals)
        # Re-resolve users if recipient fields changed (only in draft)
        recipient_fields = {'recipient_type', 'user_id', 'department_id', 'role_id'}
        if recipient_fields & set(vals.keys()):
            for record in self:
                if record.document_id.state == 'draft':
                    record.routing_user_ids.sudo().unlink()
                    record._resolve_users()
        return result

    def unlink(self):
        for record in self:
            if record.document_id.state != 'draft':
                raise UserError(
                    _("Cannot delete routing after document has been sent.")
                )
        return super().unlink()

    # === User Resolution ===
    def _resolve_users(self):
        """Resolve users from recipient type and create routing.user records."""
        self.ensure_one()
        RoutingUser = self.env["sarabun.document.routing.user"].sudo()
        vals_list = []

        if self.recipient_type == "user" and self.user_id:
            vals_list.append({
                "routing_id": self.id,
                "user_id": self.user_id.id,
                "sequence": 10,
                "resolution_reason": "direct",
            })
        elif self.recipient_type == "department" and self.department_id:
            seq = 10
            if self.department_id.sarabun_officer_ids:
                for user in self.department_id.sarabun_officer_ids:
                    vals_list.append({
                        "routing_id": self.id,
                        "user_id": user.id,
                        "sequence": seq,
                        "resolution_reason": "dept_officer",
                    })
                    seq += 10
            elif (
                self.department_id.manager_id
                and self.department_id.manager_id.user_id
            ):
                vals_list.append({
                    "routing_id": self.id,
                    "user_id": self.department_id.manager_id.user_id.id,
                    "sequence": seq,
                    "resolution_reason": "dept_manager",
                })
        elif self.recipient_type == "role" and self.role_id:
            role_users = self.role_id.get_users_for_document(self.document_id)
            reason = (
                "role_static" if self.role_id.role_type == "static"
                else "role_dynamic"
            )
            seq = 10
            for user in role_users:
                vals_list.append({
                    "routing_id": self.id,
                    "user_id": user.id,
                    "sequence": seq,
                    "resolution_reason": reason,
                })
                seq += 10

        if vals_list:
            RoutingUser.create(vals_list)

    def action_refresh_users(self):
        """Refresh resolved users for this routing (draft only)."""
        self.ensure_one()
        if self.document_id.state != "draft":
            raise UserError(_("Cannot refresh users after document has been sent."))
        self.routing_user_ids.sudo().unlink()
        self._resolve_users()

    # === Computed Fields ===
    @api.depends("routing_user_ids", "routing_user_ids.user_id")
    def _compute_routing_user_info(self):
        for record in self:
            users = record.routing_user_ids.mapped("user_id")
            record.routing_user_count = len(users)
            if users:
                names = users[:3].mapped("name")
                extra = len(users) - 3
                text = ", ".join(names)
                if extra > 0:
                    text += _(" (+%d)") % extra
                record.routing_user_names = text
            else:
                record.routing_user_names = False

    @api.depends(
        "document_id.recipient_ids",
        "document_id.recipient_ids.state",
        "document_id.recipient_ids.routing_id",
    )
    def _compute_state(self):
        for routing in self:
            recipients = routing.document_id.recipient_ids.filtered(
                lambda r: r.routing_id.id == routing.id
            )
            if not recipients:
                routing.state = "draft"
            elif any(r.state == "rejected" for r in recipients):
                routing.state = "rejected"
            elif all(r.state in ("acknowledged", "approved") for r in recipients):
                routing.state = "completed"
            else:
                routing.state = "active"

    @api.depends("recipient_type", "user_id", "department_id", "role_id")
    def _compute_recipient_name(self):
        for record in self:
            if record.recipient_type == "user" and record.user_id:
                record.recipient_name = record.user_id.name
            elif record.recipient_type == "department" and record.department_id:
                record.recipient_name = record.department_id.name
            elif record.recipient_type == "role" and record.role_id:
                record.recipient_name = record.role_id.name
            else:
                record.recipient_name = False

    # === Actions ===
    def action_open_edit_wizard(self):
        """Open wizard to edit this routing"""
        self.ensure_one()
        return {
            "name": _("Edit Routing"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.routing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_document_id": self.document_id.id,
                "default_routing_id": self.id,
            },
        }

    # === Constraints ===
    @api.constrains("recipient_type", "user_id", "department_id", "role_id")
    def _check_recipient(self):
        for record in self:
            if record.recipient_type == "user" and not record.user_id:
                raise UserError(_("Please select a user for user-type recipient."))
            if record.recipient_type == "department" and not record.department_id:
                raise UserError(_("Please select a department for routing."))
            if record.recipient_type == "role" and not record.role_id:
                raise UserError(
                    _("Please select a role/position for role-type recipient.")
                )
