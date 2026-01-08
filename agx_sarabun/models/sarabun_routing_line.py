# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SarabunRoutingLine(models.Model):
    _name = "sarabun.routing.line"
    _description = "Sarabun Routing Line"
    _order = "sequence, id"
    _inherit = ["mail.thread"]

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

    # === Line State ===
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("acknowledged", "Acknowledged"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("forwarded", "Forwarded"),
        ],
        string="Status",
        default="pending",
        tracking=True,
    )

    # === Action Details ===
    actioned_by = fields.Many2one(
        comodel_name="res.users",
        string="Actioned By",
        readonly=True,
    )
    actioned_date = fields.Datetime(
        string="Action Date",
        readonly=True,
    )
    comment = fields.Text(
        string="Comment",
    )

    # === Signing Position ===
    signed_as_role_id = fields.Many2one(
        comodel_name="sarabun.role",
        string="Signed As",
        readonly=True,
        help="Position/title used when signing this document",
    )
    signed_as_text = fields.Char(
        string="Signed As (Display)",
        readonly=True,
        help="Display text of signing position",
    )

    # === Forwarding ===
    forward_to_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Forward To User",
    )
    forward_to_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Forward To Department",
    )

    # === Notifications ===
    is_notified = fields.Boolean(
        string="Notified",
        default=False,
    )
    notification_date = fields.Datetime(
        string="Notification Date",
    )

    # === Related Fields ===
    document_state = fields.Selection(
        related="document_id.state",
        string="Document State",
    )
    document_subject = fields.Char(
        related="document_id.subject",
        string="Subject",
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

    # === Actions ===
    def action_acknowledge(self):
        """Acknowledge document receipt - opens signing wizard"""
        self.ensure_one()
        self._check_can_action()

        return self._open_signing_wizard("acknowledge")

    def action_approve(self):
        """Approve document - opens signing wizard"""
        self.ensure_one()
        self._check_can_action()

        if self.routing_type != "approve":
            raise UserError(_("This routing line is not for approval."))

        return self._open_signing_wizard("approve")

    def _open_signing_wizard(self, action_type):
        """Open the signing wizard for user to select signing position"""
        self.ensure_one()

        # Get available roles for current user
        available_roles = self.env["sarabun.role"].get_user_roles()

        if not available_roles:
            raise UserError(
                _("You don't have any roles assigned. Please contact administrator.")
            )

        return {
            "name": _("Select Signing Position"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.signing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_routing_line_id": self.id,
                "default_action_type": action_type,
            },
        }

    def action_do_acknowledge(self, signed_as_role_id):
        """Actually acknowledge with signing position"""
        self.ensure_one()
        self._check_can_action()

        role = self.env["sarabun.role"].browse(signed_as_role_id)

        self.write(
            {
                "state": "acknowledged",
                "actioned_by": self.env.user.id,
                "actioned_date": fields.Datetime.now(),
                "signed_as_role_id": signed_as_role_id,
                "signed_as_text": role.name if role else False,
            }
        )

        self.document_id.message_post(
            body=_("Document acknowledged by %s as %s")
            % (self.env.user.name, role.name if role else "-"),
            message_type="notification",
        )

        self.document_id._check_routing_completion()

    def action_do_approve(self, signed_as_role_id):
        """Actually approve with signing position"""
        self.ensure_one()
        self._check_can_action()

        if self.routing_type != "approve":
            raise UserError(_("This routing line is not for approval."))

        role = self.env["sarabun.role"].browse(signed_as_role_id)

        self.write(
            {
                "state": "approved",
                "actioned_by": self.env.user.id,
                "actioned_date": fields.Datetime.now(),
                "signed_as_role_id": signed_as_role_id,
                "signed_as_text": role.name if role else False,
            }
        )

        self.document_id.message_post(
            body=_("Document approved by %s as %s")
            % (self.env.user.name, role.name if role else "-"),
            message_type="notification",
        )

        self.document_id._check_routing_completion()

    def action_reject(self):
        """Reject document - opens wizard for comment"""
        self.ensure_one()
        self._check_can_action()

        return {
            "name": _("Reject Document"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.routing.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_routing_line_id": self.id,
            },
        }

    def action_do_reject(self, comment):
        """Actually reject the document with comment"""
        self.ensure_one()
        self._check_can_action()

        if not comment:
            raise UserError(_("Please provide a rejection reason."))

        self.write(
            {
                "state": "rejected",
                "comment": comment,
                "actioned_by": self.env.user.id,
                "actioned_date": fields.Datetime.now(),
            }
        )

        self.document_id._check_routing_completion()

    def action_forward(self):
        """Forward document - opens wizard for recipient selection"""
        self.ensure_one()
        self._check_can_action()

        return {
            "name": _("Forward Document"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.routing.forward.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_routing_line_id": self.id,
            },
        }

    def action_do_forward(self, forward_to_user_id=False, forward_to_department_id=False, comment=False):
        """Actually forward the document"""
        self.ensure_one()
        self._check_can_action()

        if not forward_to_user_id and not forward_to_department_id:
            raise UserError(_("Please specify a forward recipient."))

        # Create new routing line for forward recipient
        new_line_vals = {
            "document_id": self.document_id.id,
            "sequence": self.sequence + 5,
            "routing_type": self.routing_type,
            "recipient_type": "user" if forward_to_user_id else "department",
            "user_id": forward_to_user_id if forward_to_user_id else False,
            "department_id": forward_to_department_id if forward_to_department_id else False,
        }

        new_line = self.env["sarabun.routing.line"].create(new_line_vals)
        new_line._send_notification()

        self.write(
            {
                "state": "forwarded",
                "comment": comment,
                "forward_to_user_id": forward_to_user_id,
                "forward_to_department_id": forward_to_department_id,
                "actioned_by": self.env.user.id,
                "actioned_date": fields.Datetime.now(),
            }
        )

        forward_to_name = ""
        if forward_to_user_id:
            forward_to_name = self.env["res.users"].browse(forward_to_user_id).name
        elif forward_to_department_id:
            forward_to_name = self.env["hr.department"].browse(forward_to_department_id).name

        self.document_id.message_post(
            body=_("Document forwarded by %s to %s")
            % (self.env.user.name, forward_to_name),
            message_type="notification",
        )

    def _check_can_action(self):
        """Check if current user can perform action on this line"""
        self.ensure_one()

        if self.state != "pending":
            raise UserError(_("This routing line has already been processed."))

        if self.document_id.state != "sent":
            raise UserError(_("Document is not in sent state."))

        can_action = False

        if self.recipient_type == "user":
            can_action = self.user_id == self.env.user
        elif self.recipient_type == "department":
            if self.department_id:
                # Check if user is a sarabun officer
                if self.env.user in self.department_id.sarabun_officer_ids:
                    can_action = True
                # Or if user is manager of department
                elif self.department_id.manager_id:
                    can_action = self.department_id.manager_id.user_id == self.env.user
        elif self.recipient_type == "role":
            if self.role_id:
                role_users = self.role_id.get_users_for_document(self.document_id)
                can_action = self.env.user in role_users

        if not can_action:
            raise UserError(_("You are not authorized to perform this action."))

    def _send_notification(self):
        """Send activity notification to recipient"""
        self.ensure_one()

        if self.is_notified:
            return

        users_to_notify = self.env["res.users"]

        if self.recipient_type == "user":
            users_to_notify = self.user_id
        elif self.recipient_type == "department" and self.department_id:
            # Check for sarabun officers first
            if self.department_id.sarabun_officer_ids:
                users_to_notify = self.department_id.sarabun_officer_ids
            # Fallback to department manager
            elif self.department_id.manager_id:
                users_to_notify = self.department_id.manager_id.user_id
        elif self.recipient_type == "role" and self.role_id:
            users_to_notify = self.role_id.get_users_for_document(self.document_id)

        routing_type_labels = dict(self._fields["routing_type"].selection)
        action_label = routing_type_labels.get(self.routing_type, self.routing_type)

        for user in users_to_notify:
            self.document_id.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=user.id,
                summary=_("Document requires your action: %s") % action_label,
                note=_("Document: %s\nSubject: %s")
                % (self.document_id.name, self.document_id.subject),
            )

        self.write(
            {
                "is_notified": True,
                "notification_date": fields.Datetime.now(),
            }
        )

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
