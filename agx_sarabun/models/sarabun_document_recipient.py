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

    # === CC Forward ===
    is_cc = fields.Boolean(
        string="CC (Read Only)",
        default=False,
        help="CC recipients have read-only access, cannot take routing actions",
    )
    forwarded_by_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Forwarded By",
        readonly=True,
    )
    forwarded_by_recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Forwarded From",
        readonly=True,
    )
    forward_comment = fields.Text(
        string="Forward Comment",
    )

    # === Delegation ===
    is_delegated = fields.Boolean(
        string="Delegated",
        default=False,
        help="This recipient was created via delegation",
    )
    delegated_by_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Delegated By",
        readonly=True,
    )
    delegated_by_recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Delegated From",
        readonly=True,
    )
    delegation_chain_ids = fields.One2many(
        comodel_name="sarabun.document.recipient",
        inverse_name="delegated_by_recipient_id",
        string="Delegated To",
    )

    # === Central Correspondence Dispatch ===
    needs_dispatch = fields.Boolean(
        string="Needs Dispatch",
        default=False,
        help="Pending dispatch by central correspondence clerk",
    )
    dispatched_by_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Dispatched By",
        readonly=True,
    )
    dispatched_date = fields.Datetime(
        string="Dispatched Date",
        readonly=True,
    )
    dispatch_note = fields.Text(
        string="Dispatch Note",
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

        # Mark inbox as read
        self._mark_inbox_read_for_user(self.env.user)

        # Trigger callback on origin
        self.document_id._trigger_origin_action_callback(self, "acknowledge")

        # Execute step hook on origin record
        if self.routing_line_id:
            self.document_id._execute_step_hook(self.routing_line_id)

        # Resolve delegation chain
        self._resolve_delegation_chain()

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

        # Mark inbox as read
        self._mark_inbox_read_for_user(self.env.user)

        # Trigger callback on origin
        self.document_id._trigger_origin_action_callback(self, "approve")

        # Execute step hook on origin record
        if self.routing_line_id:
            self.document_id._execute_step_hook(self.routing_line_id)

        # Resolve delegation chain
        self._resolve_delegation_chain()

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

        # Mark inbox as read
        self._mark_inbox_read_for_user(self.env.user)

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

        if self.is_cc:
            raise UserError(_("CC recipients cannot take routing actions."))

        if self.needs_dispatch:
            raise UserError(
                _("This document must be dispatched by the "
                  "correspondence office first.")
            )

        can_action = self._can_user_access()

        # Walk delegation chain — delegator can act on delegated recipient
        if not can_action and self.delegated_by_recipient_id:
            parent = self.delegated_by_recipient_id
            while parent:
                if parent._can_user_access():
                    can_action = True
                    break
                parent = parent.delegated_by_recipient_id

        if not can_action:
            raise UserError(_("You are not authorized to perform this action."))

    def _get_users_to_notify(self):
        """Get users who should receive notification for this recipient."""
        self.ensure_one()
        # If needs dispatch, notify clerks instead of actual recipient
        if self.needs_dispatch:
            dept = self._get_recipient_department()
            if dept and dept.sarabun_officer_ids:
                return dept.sarabun_officer_ids
            # Fallback: no clerks, clear dispatch flag and notify normally
            self.needs_dispatch = False

        if self.recipient_type == "user":
            return self.user_id or self.env["res.users"]
        elif self.recipient_type == "department" and self.department_id:
            if self.department_id.sarabun_officer_ids:
                return self.department_id.sarabun_officer_ids
            elif self.department_id.manager_id:
                return self.department_id.manager_id.user_id
        elif self.recipient_type == "role" and self.role_id:
            return self.role_id.get_users_for_document(self.document_id)
        return self.env["res.users"]

    def _get_recipient_department(self):
        """Get the department associated with this recipient."""
        self.ensure_one()
        if self.recipient_type == "department" and self.department_id:
            return self.department_id
        if self.recipient_type == "user" and self.user_id:
            emp = self.user_id.employee_id
            if emp and emp.department_id:
                return emp.department_id
        return False

    def _send_notification(self):
        """Send activity notification to recipient"""
        self.ensure_one()

        if self.is_notified:
            return

        users_to_notify = self._get_users_to_notify()

        # Create per-user inbox records (one per document per user)
        Inbox = self.env["sarabun.inbox"].sudo()
        for user in users_to_notify:
            # Check if inbox already exists for this user-document combination
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
        for user in users_to_notify:
            self.env['bus.bus']._sendone(
                user.partner_id,
                'sarabun_inbox/updated',
                {
                    'refresh': True,
                    'subject': self.document_id.subject or self.document_id.name,
                    'document_id': self.document_id.id,
                }
            )

        # Send email notification
        self.document_id._send_sarabun_email(
            users_to_notify,
            "agx_sarabun.email_template_sarabun_new_document",
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

        # Central correspondence clerk access
        if self.needs_dispatch:
            dept = self._get_recipient_department()
            if dept and user in dept.sarabun_officer_ids:
                return True
            return False

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

    # === Delegation ===
    def action_delegate(self):
        """Open delegation wizard."""
        self.ensure_one()
        if self.state != "new":
            raise UserError(_("Can only delegate pending actions."))
        if self.is_cc:
            raise UserError(_("CC recipients cannot delegate."))
        if not self._can_user_access():
            raise UserError(
                _("You are not authorized to delegate this action.")
            )
        return {
            "name": _("Delegate Action"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.delegate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_recipient_id": self.id},
        }

    def _resolve_delegation_chain(self):
        """When one recipient in a chain acts, resolve all others."""
        if not self.delegated_by_recipient_id and not self.delegation_chain_ids:
            return
        # Find root of delegation chain
        root = self
        while root.delegated_by_recipient_id:
            root = root.delegated_by_recipient_id
        # Collect all in chain
        all_in_chain = self._collect_delegation_chain(root)
        # Mark siblings as resolved
        siblings = all_in_chain.filtered(
            lambda r: r.id != self.id and r.state == "new"
        )
        now = fields.Datetime.now()
        for sibling in siblings:
            sibling.write({
                "state": self.state,
                "actioned_by": self.env.user.id,
                "actioned_date": now,
                "comment": _("Resolved: action taken by %s")
                % self.env.user.name,
            })
        # Notify all users in chain (except actor)
        users_to_notify = self.env["res.users"]
        for r in all_in_chain.filtered(lambda r: r.id != self.id):
            if r.user_id:
                users_to_notify |= r.user_id
        if users_to_notify:
            self.document_id._send_sarabun_email(
                users_to_notify,
                "agx_sarabun.email_template_sarabun_action_taken",
            )

    def _collect_delegation_chain(self, root):
        """Recursively collect all recipients in a delegation chain."""
        result = root
        for child in root.delegation_chain_ids:
            result |= self._collect_delegation_chain(child)
        return result

    # === Central Correspondence Dispatch ===
    def action_dispatch(self):
        """Open dispatch wizard for central correspondence clerk."""
        self.ensure_one()
        if not self.needs_dispatch:
            raise UserError(_("This recipient does not need dispatch."))
        dept = self._get_recipient_department()
        if not dept or self.env.user not in dept.sarabun_officer_ids:
            raise UserError(
                _("Only sarabun officers can dispatch documents.")
            )
        return {
            "name": _("Dispatch Document"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.dispatch.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_recipient_id": self.id},
        }
