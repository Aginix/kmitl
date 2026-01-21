# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SarabunDocumentRecipient(models.Model):
    """
    Tracks document delivery and actions.
    Created from routing_line when document is sent.
    """

    _name = "sarabun.document.recipient"
    _description = "Sarabun Document Recipient"
    _order = "sequence, id"
    _inherit = ["mail.thread"]

    # === Links ===
    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
        ondelete="cascade",
        index=True,
    )
    routing_line_id = fields.Many2one(
        comodel_name="sarabun.routing.line",
        string="Routing Line",
        ondelete="set null",
        help="Original routing line this recipient was created from",
    )

    # === Copied from Routing Line (Snapshot) ===
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
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
    department_text = fields.Char(
        string="Department Text",
    )
    role_id = fields.Many2one(
        comodel_name="sarabun.role",
        string="Role/Position",
    )
    recipient_name = fields.Char(
        string="Recipient",
        compute="_compute_recipient_name",
        store=True,
    )

    # === State ===
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("acknowledged", "Acknowledged"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="new",
        tracking=True,
    )

    # === Timestamps ===
    # Note: use create_date as sent_date (recipient created = sent to recipient)
    read_date = fields.Datetime(
        string="Read Date",
        readonly=True,
        help="When recipient first opened the document",
    )
    actioned_date = fields.Datetime(
        string="Action Date",
        readonly=True,
        help="When recipient acknowledged/approved/rejected",
    )

    # === Action Details ===
    actioned_by = fields.Many2one(
        comodel_name="res.users",
        string="Actioned By",
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
    )
    signed_as_text = fields.Char(
        string="Signed As (Display)",
        readonly=True,
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
    document_name = fields.Char(
        related="document_id.name",
        string="Document Number",
    )

    # === Computed Fields ===
    @api.depends("recipient_type", "user_id", "department_id", "department_text", "role_id")
    def _compute_recipient_name(self):
        for record in self:
            if record.recipient_type == "user" and record.user_id:
                record.recipient_name = record.user_id.name
            elif record.recipient_type == "department":
                record.recipient_name = record.department_text or (
                    record.department_id.name if record.department_id else False
                )
            elif record.recipient_type == "role" and record.role_id:
                record.recipient_name = record.role_id.name
            else:
                record.recipient_name = False

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
            raise UserError(_("This recipient is not for approval."))

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
                "default_recipient_id": self.id,
                "default_action_type": action_type,
            },
        }

    def action_do_acknowledge(self, signed_as_role_id):
        """Actually acknowledge with signing position"""
        self.ensure_one()
        self._check_can_action()

        role = self.env["sarabun.role"].browse(signed_as_role_id)

        self.write({
            "state": "acknowledged",
            "actioned_by": self.env.user.id,
            "actioned_date": fields.Datetime.now(),
            "signed_as_role_id": signed_as_role_id,
            "signed_as_text": role.name if role else False,
        })

        self.document_id.message_post(
            body=_("Document acknowledged by %s as %s")
            % (self.env.user.name, role.name if role else "-"),
            message_type="notification",
        )

        # Mark activities as done
        self._mark_activities_done()

        # Trigger callback on origin
        self.document_id._trigger_origin_action_callback(self, "acknowledge")

        # Activate next recipient
        self.document_id._activate_next_recipient()

    def action_do_approve(self, signed_as_role_id):
        """Actually approve with signing position"""
        self.ensure_one()
        self._check_can_action()

        if self.routing_type != "approve":
            raise UserError(_("This recipient is not for approval."))

        role = self.env["sarabun.role"].browse(signed_as_role_id)

        self.write({
            "state": "approved",
            "actioned_by": self.env.user.id,
            "actioned_date": fields.Datetime.now(),
            "signed_as_role_id": signed_as_role_id,
            "signed_as_text": role.name if role else False,
        })

        self.document_id.message_post(
            body=_("Document approved by %s as %s")
            % (self.env.user.name, role.name if role else "-"),
            message_type="notification",
        )

        # Mark activities as done
        self._mark_activities_done()

        # Trigger callback on origin
        self.document_id._trigger_origin_action_callback(self, "approve")

        # Activate next recipient
        self.document_id._activate_next_recipient()

    def action_reject(self):
        """Reject document - opens wizard for comment"""
        self.ensure_one()
        self._check_can_action()

        return {
            "name": _("Reject Document"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.recipient.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_recipient_id": self.id,
            },
        }

    def action_do_reject(self, comment):
        """Actually reject the document with comment"""
        self.ensure_one()
        self._check_can_action()

        if not comment:
            raise UserError(_("Please provide a rejection reason."))

        self.write({
            "state": "rejected",
            "comment": comment,
            "actioned_by": self.env.user.id,
            "actioned_date": fields.Datetime.now(),
        })

        self.document_id.message_post(
            body=_("Document rejected by %s.\nReason: %s")
            % (self.env.user.name, comment),
            message_type="notification",
        )

        # Mark activities as done
        self._mark_activities_done()

        # Trigger callback on origin
        self.document_id._trigger_origin_action_callback(self, "reject")

        # Notify origin about rejection
        self.document_id._on_routing_rejected(self)

    def _check_can_action(self):
        """Check if current user can perform action on this recipient"""
        self.ensure_one()

        if self.state != "new":
            raise UserError(_("This recipient has already been actioned."))

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
            # Send to all sarabun officers
            if self.department_id.sarabun_officer_ids:
                users_to_notify = self.department_id.sarabun_officer_ids
            # Fallback to department manager
            elif self.department_id.manager_id:
                users_to_notify = self.department_id.manager_id.user_id
        elif self.recipient_type == "role" and self.role_id:
            users_to_notify = self.role_id.get_users_for_document(self.document_id)

        routing_type_labels = dict(self._fields["routing_type"].selection)
        action_label = routing_type_labels.get(self.routing_type, self.routing_type)

        # for user in users_to_notify:
        #     self.document_id.activity_schedule(
        #         "mail.mail_activity_data_todo",
        #         user_id=user.id,
        #         summary=_("Document requires your action: %s") % action_label,
        #         note=_("Document: %s\nSubject: %s")
        #         % (self.document_id.name, self.document_id.subject),
        #     )

        self.write({
            "is_notified": True,
            "notification_date": fields.Datetime.now(),
        })

    def _mark_activities_done(self):
        """Mark related activities as done"""
        activities = self.document_id.activity_ids.filtered(
            lambda a: a.user_id == self.env.user
        )
        activities.action_feedback(feedback=_("Action completed"))

    def mark_as_read(self):
        """Mark recipient as read (first time opening)"""
        self.ensure_one()
        if self.state == "new" and not self.read_date:
            self.read_date = fields.Datetime.now()

    def read(self, fields=None, load="_classic_read"):
        """Override to track read_date when recipient form is opened"""
        result = super().read(fields=fields, load=load)

        # Only track when opening form (reading with key fields)
        if fields is None or "document_id" in fields:
            for record in self:
                if record._can_user_access():
                    record.sudo().mark_as_read()

        return result

    def _can_user_access(self, user=None):
        """Check if user can access this recipient (for Inbox display)"""
        self.ensure_one()
        if user is None:
            user = self.env.user

        if self.recipient_type == "user":
            return self.user_id == user
        elif self.recipient_type == "department" and self.department_id:
            # Sarabun officers or manager
            if user in self.department_id.sarabun_officer_ids:
                return True
            if self.department_id.manager_id:
                return self.department_id.manager_id.user_id == user
        elif self.recipient_type == "role" and self.role_id:
            role_users = self.role_id.get_users_for_document(self.document_id)
            return user in role_users

        return False
