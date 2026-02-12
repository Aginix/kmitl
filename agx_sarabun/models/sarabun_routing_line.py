# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

ROUTING_TYPE_SEQUENCE = {
    "acknowledge": 10,
    "approve": 100,
}


class SarabunRoutingLine(models.Model):
    """
    Routing step definition - defines the type and recipient for each step.
    Resolved users are stored in sarabun.recipient.user immediately.
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
    action_policy = fields.Selection(
        selection=[
            ("first", "First to Act"),
            ("all", "All Must Act"),
            ("majority", "Majority Must Act"),
        ],
        string="Action Policy",
        default="first",
    )

    # === Resolved Users ===
    preview_user_ids = fields.One2many(
        comodel_name="sarabun.recipient.user",
        inverse_name="routing_line_id",
        string="Resolved Users",
    )
    preview_user_count = fields.Integer(
        string="User Count",
        compute="_compute_preview_user_info",
        store=True,
    )
    preview_user_names = fields.Char(
        string="Resolved Users",
        compute="_compute_preview_user_info",
        store=True,
    )

    # === Status from Recipient (for display) ===
    document_state = fields.Selection(
        related="document_id.state",
        string="Document State",
    )
    recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Recipient Record",
        compute="_compute_recipient_status",
        store=False,
    )
    recipient_state = fields.Selection(
        selection=[
            ("waiting", "Waiting"),
            ("new", "New"),
            ("acknowledged", "Acknowledged"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        compute="_compute_recipient_status",
        store=False,
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
        # Check if document has been sent
        for record in self:
            if record.document_id.state != 'draft':
                raise UserError(
                    _("Cannot modify routing line after document has been sent.")
                )

        if 'routing_type' in vals and not vals.get('sequence'):
            vals['sequence'] = ROUTING_TYPE_SEQUENCE.get(vals['routing_type'], 10)
        result = super().write(vals)
        # Re-resolve users if recipient fields changed (only in draft)
        recipient_fields = {'recipient_type', 'user_id', 'department_id', 'role_id'}
        if recipient_fields & set(vals.keys()):
            for record in self:
                if record.document_id.state == 'draft':
                    record.preview_user_ids.filtered(
                        lambda u: not u.recipient_id
                    ).sudo().unlink()
                    record._resolve_users()
        return result

    def unlink(self):
        # Check if document has been sent
        for record in self:
            if record.document_id.state != 'draft':
                raise UserError(
                    _("Cannot delete routing line after document has been sent.")
                )
        # Delete unadopted user records (not yet linked to a recipient)
        unadopted = self.mapped("preview_user_ids").filtered(
            lambda u: not u.recipient_id
        )
        unadopted.sudo().unlink()
        return super().unlink()

    # === User Resolution ===
    def _resolve_users(self):
        """Resolve users from recipient type and create recipient.user records."""
        self.ensure_one()
        RecipientUser = self.env["sarabun.recipient.user"].sudo()
        vals_list = []

        if self.recipient_type == "user" and self.user_id:
            vals_list.append({
                "routing_line_id": self.id,
                "user_id": self.user_id.id,
                "sequence": 10,
                "resolution_reason": "direct",
            })
        elif self.recipient_type == "department" and self.department_id:
            seq = 10
            if self.department_id.sarabun_officer_ids:
                for user in self.department_id.sarabun_officer_ids:
                    vals_list.append({
                        "routing_line_id": self.id,
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
                    "routing_line_id": self.id,
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
                    "routing_line_id": self.id,
                    "user_id": user.id,
                    "sequence": seq,
                    "resolution_reason": reason,
                })
                seq += 10

        if vals_list:
            RecipientUser.create(vals_list)

    def action_refresh_users(self):
        """Refresh resolved users for this routing line (draft only)."""
        self.ensure_one()
        if self.document_id.state != "draft":
            raise UserError(_("Cannot refresh users after document has been sent."))
        self.preview_user_ids.filtered(
            lambda u: not u.recipient_id
        ).sudo().unlink()
        self._resolve_users()

    # === Computed Fields ===
    @api.depends("preview_user_ids", "preview_user_ids.user_id")
    def _compute_preview_user_info(self):
        for record in self:
            users = record.preview_user_ids.mapped("user_id")
            record.preview_user_count = len(users)
            if users:
                names = users[:3].mapped("name")
                extra = len(users) - 3
                text = ", ".join(names)
                if extra > 0:
                    text += _(" (+%d)") % extra
                record.preview_user_names = text
            else:
                record.preview_user_names = False

    @api.depends(
        "document_id.recipient_ids",
        "document_id.recipient_ids.state",
        "document_id.recipient_ids.routing_line_id",
    )
    def _compute_recipient_status(self):
        for line in self:
            recipient = line.document_id.recipient_ids.filtered(
                lambda r: r.routing_line_id.id == line.id
            )[:1]
            line.recipient_id = recipient
            line.recipient_state = recipient.state if recipient else "waiting"

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
        """Open wizard to edit this routing line"""
        self.ensure_one()
        return {
            "name": _("Edit Routing"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.routing.line.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_document_id": self.document_id.id,
                "default_routing_line_id": self.id,
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
