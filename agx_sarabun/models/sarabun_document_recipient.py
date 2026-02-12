# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SarabunDocumentRecipient(models.Model):
    """
    Tracks document delivery and actions per user.
    Created from routing when document reaches that step.
    One record per user (flattened).
    """

    _name = "sarabun.document.recipient"
    _description = "Document Recipient"
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
    routing_id = fields.Many2one(
        comodel_name="sarabun.document.routing",
        string="Routing",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        index=True,
    )

    # === Snapshot from Routing (for audit trail) ===
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
    recipient_name = fields.Char(
        string="Recipient",
        compute="_compute_recipient_name",
        store=True,
    )

    # === State ===
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("acknowledged", "Acknowledged"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="pending",
        required=True,
        tracking=True,
    )

    # === Timestamps ===
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
    @api.depends("recipient_type", "user_id", "routing_id")
    def _compute_recipient_name(self):
        for record in self:
            if record.routing_id:
                record.recipient_name = record.routing_id.recipient_name
            elif record.user_id:
                record.recipient_name = record.user_id.name
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

        self._mark_inbox_read_for_user(self.env.user)
        self._mark_activities_done()
        self.document_id._trigger_origin_action_callback(self, "acknowledge")
        self.document_id._check_routing_completion(self.routing_id)

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

        self._mark_inbox_read_for_user(self.env.user)
        self._mark_activities_done()
        self.document_id._trigger_origin_action_callback(self, "approve")
        self.document_id._check_routing_completion(self.routing_id)

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

        self._mark_activities_done()
        self._mark_inbox_read_for_user(self.env.user)
        self.document_id._trigger_origin_action_callback(self, "reject")
        self.document_id._on_routing_rejected(self)

    def _check_can_action(self):
        """Check if current user can perform action on this recipient"""
        self.ensure_one()

        if self.state != "pending":
            raise UserError(_("This recipient has already been actioned."))

        if self.document_id.state != "sent":
            raise UserError(_("Document is not in sent state."))

        if self.user_id != self.env.user:
            raise UserError(_("You are not authorized to perform this action."))

    def _send_notification(self):
        """Send notification to recipient user"""
        self.ensure_one()

        if self.is_notified:
            return

        user = self.user_id

        # Create inbox record (one per document per user)
        Inbox = self.env["sarabun.inbox"].sudo()
        existing = Inbox.search([
            ("user_id", "=", user.id),
            ("document_id", "=", self.document_id.id),
        ], limit=1)
        if not existing:
            Inbox.create({
                "user_id": user.id,
                "document_id": self.document_id.id,
                "is_read": False,
            })

        # Send bus notification for real-time systray update
        self.env['bus.bus']._sendone(
            user.partner_id,
            'sarabun_inbox/updated',
            {
                'refresh': True,
                'subject': self.document_id.subject or self.document_id.name,
                'document_id': self.document_id.id,
            }
        )

        self.write({
            "is_notified": True,
            "notification_date": fields.Datetime.now(),
        })

    def _mark_inbox_read_for_user(self, user):
        """Mark inbox entries as read for a specific user"""
        inbox = self.env["sarabun.inbox"].sudo().search([
            ("user_id", "=", user.id),
            ("document_id", "=", self.document_id.id),
            ("is_read", "=", False),
        ])
        if inbox:
            inbox.write({"is_read": True})

    def _mark_activities_done(self):
        """Mark related activities as done"""
        activities = self.document_id.activity_ids.filtered(
            lambda a: a.user_id == self.env.user
        )
        activities.action_feedback(feedback=_("Action completed"))

    def mark_as_read(self):
        """Mark recipient as read (first time opening)"""
        self.ensure_one()
        if self.state == "pending" and not self.read_date:
            self.read_date = fields.Datetime.now()

    def _can_user_access(self, user=None):
        """Check if user can access this recipient"""
        self.ensure_one()
        if user is None:
            user = self.env.user
        return self.user_id == user
