# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

READONLY_STATES = {
    "sent": [("readonly", True)],
    "completed": [("readonly", True)],
    "cancelled": [("readonly", True)],
}


class SarabunDocument(models.Model):
    _name = "sarabun.document"
    _description = "Sarabun Document"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "subject"]

    # === Document Identification ===
    name = fields.Char(
        string="Document Number",
        required=True,
        readonly=True,
        copy=False,
        default="/",
        tracking=True,
        index="trigram",
    )

    # === Numbering System ===
    document_sequence_id = fields.Many2one(
        comodel_name="sarabun.document.sequence",
        string="Document Sequence",
        states=READONLY_STATES,
        help="Select the numbering sequence to use for this document",
    )
    document_number_id = fields.Many2one(
        comodel_name="sarabun.document.number",
        string="Reserved Number",
        states=READONLY_STATES,
        help="If using a reserved number, link it here",
    )
    numbering_mode = fields.Selection(
        selection=[
            ("auto", "Use Next Available"),
            ("reserved", "Use Reserved Number"),
            ("available", "Use Available (Gap) Number"),
            ("manual", "Enter Manually"),
        ],
        string="Numbering Mode",
        default="auto",
        states=READONLY_STATES,
    )
    manual_number = fields.Integer(
        string="Manual Number",
        states=READONLY_STATES,
        help="Enter specific number when using manual mode",
    )

    # === Document Type ===
    document_type_id = fields.Many2one(
        comodel_name="sarabun.document.type",
        string="Document Type",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    document_type_code = fields.Selection(
        related="document_type_id.code",
        store=True,
    )

    # === Document Fields ===
    subject = fields.Char(
        string="Subject",
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    date = fields.Date(
        string="Document Date",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        states=READONLY_STATES,
    )
    content = fields.Html(
        string="Content",
        tracking=True,
        states=READONLY_STATES,
    )
    urgency = fields.Selection(
        selection=[
            ("normal", "Normal"),
            ("urgent", "Urgent"),
            ("very_urgent", "Very Urgent"),
            ("immediate", "Immediate"),
        ],
        string="Urgency Level",
        default="normal",
        tracking=True,
        states=READONLY_STATES,
    )
    secrecy = fields.Selection(
        selection=[
            ("normal", "Normal"),
            ("confidential", "Confidential"),
            ("secret", "Secret"),
            ("top_secret", "Top Secret"),
        ],
        string="Secrecy Level",
        default="normal",
        tracking=True,
        states=READONLY_STATES,
    )

    # === Sender / Recipient Information ===
    sender_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Sender User",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True,
    )
    sender_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Sender Department",
        default=lambda self: self._default_sender_department_id(),
        required=True,
        tracking=True,
        states=READONLY_STATES,
    )
    sender_department_name = fields.Char(
        string="Sender Department Name",
        help="Stored department name at the time of document creation",
    )
    sender_suffix = fields.Char(
        string="Sender Suffix",
        tracking=True,
        states=READONLY_STATES,
        help="Sub-department name or extension number (e.g., 'สำนักงานคณบดี' or 'ต่อ 1234')",
    )
    sender_display = fields.Char(
        string="From",
        compute="_compute_sender_display",
        store=True,
    )
    recipient = fields.Char(
        string="To",
        tracking=True,
        states=READONLY_STATES,
        help="Recipient name/department.",
    )

    # === Origin Record Link ===
    origin_model = fields.Char(
        string="Origin Model",
        readonly=True,
        index=True,
    )
    origin_res_id = fields.Integer(
        string="Origin Record ID",
        readonly=True,
        index=True,
    )
    origin_reference = fields.Char(
        string="Origin Reference",
        compute="_compute_origin_reference",
    )

    # === Workflow State ===
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    # === Routing ===
    route_template_id = fields.Many2one(
        comodel_name="sarabun.route.template",
        string="Route Template",
        states=READONLY_STATES,
    )
    routing_line_ids = fields.One2many(
        comodel_name="sarabun.routing.line",
        inverse_name="document_id",
        string="Routing",
        copy=True,
        states=READONLY_STATES,
    )

    # === Recipients (Delivery Tracking) ===
    recipient_ids = fields.One2many(
        comodel_name="sarabun.document.recipient",
        inverse_name="document_id",
        string="Recipients",
        readonly=True,
    )

    # === Computed Routing Status ===
    routing_progress = fields.Float(
        string="Routing Progress",
        compute="_compute_routing_progress",
        store=True,
    )
    pending_routing_count = fields.Integer(
        compute="_compute_routing_counts",
    )
    completed_routing_count = fields.Integer(
        compute="_compute_routing_counts",
    )

    # === References ===
    reference_ids = fields.One2many(
        comodel_name="sarabun.reference",
        inverse_name="document_id",
        string="References",
        states=READONLY_STATES,
    )
    referenced_document_ids = fields.Many2many(
        comodel_name="sarabun.document",
        relation="sarabun_document_reference_rel",
        column1="document_id",
        column2="referenced_id",
        string="Referenced Documents",
        states=READONLY_STATES,
    )

    # === Attachments ===
    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
    )
    attachment_count = fields.Integer(
        compute="_compute_attachment_count",
    )

    # === Company ===
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    # === Display name ===
    def name_get(self):
        result = []
        for record in self:
            name = record.name or _("New")
            if record.subject:
                name = f"{name} - {record.subject}"
            result.append((record.id, name))
        return result

    # === Default Methods ===
    @api.model
    def _default_sender_department_id(self):
        """Get default sender department from user's employee"""
        user = self.env.user
        if user.employee_id and user.employee_id.department_id:
            return user.employee_id.department_id.id
        return False

    # === Computed Fields ===
    @api.depends("sender_department_name", "sender_suffix")
    def _compute_sender_display(self):
        for record in self:
            parts = []
            if record.sender_department_name:
                parts.append(record.sender_department_name)
            if record.sender_suffix:
                parts.append(record.sender_suffix)
            record.sender_display = " ".join(parts) if parts else ""

    @api.depends("origin_model", "origin_res_id")
    def _compute_origin_reference(self):
        for record in self:
            if record.origin_model and record.origin_res_id:
                try:
                    origin = self.env[record.origin_model].browse(record.origin_res_id)
                    record.origin_reference = origin.display_name
                except Exception:
                    record.origin_reference = False
            else:
                record.origin_reference = False

    @api.depends("recipient_ids", "recipient_ids.state")
    def _compute_routing_progress(self):
        for record in self:
            total = len(record.recipient_ids)
            if total:
                done = len(
                    record.recipient_ids.filtered(
                        lambda r: r.state not in ("waiting", "pending")
                    )
                )
                record.routing_progress = (done / total) * 100
            else:
                record.routing_progress = 0

    @api.depends("recipient_ids", "recipient_ids.state")
    def _compute_routing_counts(self):
        for record in self:
            record.pending_routing_count = len(
                record.recipient_ids.filtered(lambda r: r.state == "pending")
            )
            record.completed_routing_count = len(
                record.recipient_ids.filtered(
                    lambda r: r.state not in ("waiting", "pending")
                )
            )

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)

    # === Onchange ===
    @api.onchange("route_template_id")
    def _onchange_route_template_id(self):
        if self.route_template_id:
            lines = []
            for tmpl_line in self.route_template_id.line_ids:
                line_vals = {
                    "sequence": tmpl_line.sequence,
                    "routing_type": tmpl_line.routing_type,
                    "recipient_type": tmpl_line.recipient_type,
                    "user_id": tmpl_line.user_id.id if tmpl_line.user_id else False,
                    "department_id": (
                        tmpl_line.department_id.id if tmpl_line.department_id else False
                    ),
                    "role_id": tmpl_line.role_id.id if tmpl_line.role_id else False,
                }
                lines.append((0, 0, line_vals))
            self.routing_line_ids = lines

    @api.onchange("document_type_id")
    def _onchange_document_type_id(self):
        if (
            self.document_type_id
            and self.document_type_id.default_route_template_id
            and not self.routing_line_ids
        ):
            self.route_template_id = self.document_type_id.default_route_template_id

    @api.onchange("numbering_mode")
    def _onchange_numbering_mode(self):
        """Clear number selection when mode changes"""
        if self.numbering_mode != "reserved":
            self.document_number_id = False
        if self.numbering_mode != "manual":
            self.manual_number = False

    @api.onchange("document_sequence_id")
    def _onchange_document_sequence_id(self):
        """Reset numbering options when sequence changes"""
        self.document_number_id = False
        self.manual_number = False
        self.numbering_mode = "auto"

    @api.onchange("sender_department_id")
    def _onchange_sender_department_id(self):
        """Copy department name and reset sequence if not matching"""
        if self.sender_department_id:
            self.sender_department_name = self.sender_department_id.name
            # Reset document_sequence_id if it doesn't match the new department
            if self.document_sequence_id:
                seq = self.document_sequence_id
                if seq.department_ids and self.sender_department_id not in seq.department_ids:
                    self.document_sequence_id = False
                    self.document_number_id = False
                    self.manual_number = False
        else:
            self.sender_department_name = False

    # === Actions ===
    def action_send(self):
        """Send document and create recipients from routing lines"""
        for document in self:
            if document.state != "draft":
                raise UserError(_("Only draft documents can be sent."))

            if not document.routing_line_ids:
                raise UserError(_("Please add at least one routing line."))

            # Generate document number
            if document.name == "/":
                document.name = document._generate_document_number()

            # Create recipients from routing lines (all start as waiting)
            Recipient = self.env["sarabun.document.recipient"]
            for line in document.routing_line_ids:
                Recipient.create({
                    "document_id": document.id,
                    "routing_line_id": line.id,
                    "sequence": line.sequence,
                    "routing_type": line.routing_type,
                    "recipient_type": line.recipient_type,
                    "user_id": line.user_id.id if line.user_id else False,
                    "department_id": line.department_id.id if line.department_id else False,
                    "department_text": line.department_text,
                    "role_id": line.role_id.id if line.role_id else False,
                    "state": "waiting",
                })

            document.state = "sent"

            # Activate first recipient (sequential delivery)
            document._activate_next_recipient()

            document.message_post(
                body=_("Document sent for routing by %s") % document.sender_user_id.name,
                message_type="notification",
            )

    def action_cancel(self):
        """Cancel draft document - like email, once sent cannot be cancelled"""
        for document in self:
            if document.state != "draft":
                raise UserError(_("Only draft documents can be cancelled. Once sent, documents cannot be cancelled."))

            document.state = "cancelled"
            document.message_post(
                body=_("Document cancelled."),
                message_type="notification",
            )

    def action_view_origin(self):
        """View origin record"""
        self.ensure_one()
        if not self.origin_model or not self.origin_res_id:
            raise UserError(_("No origin record linked to this document."))
        return {
            "type": "ir.actions.act_window",
            "res_model": self.origin_model,
            "res_id": self.origin_res_id,
            "view_mode": "form",
            "target": "current",
        }

    def action_lookup_recipient(self):
        """Open department lookup wizard for recipient"""
        self.ensure_one()
        return {
            "name": _("Select Department"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.department.lookup.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_target_model": "sarabun.document",
                "default_target_record_id": self.id,
                "default_target_field": "recipient",
            },
        }

    def action_select_number(self):
        """Open number selection wizard"""
        self.ensure_one()
        if not self.document_sequence_id:
            raise UserError(_("Please select a document sequence first."))
        return {
            "name": _("Select Document Number"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.number.selection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_document_id": self.id,
                "default_sequence_id": self.document_sequence_id.id,
            },
        }

    # === Helper Methods ===
    def _generate_document_number(self):
        """Generate document number based on numbering mode"""
        self.ensure_one()

        # Use document sequence if specified
        if self.document_sequence_id:
            if self.numbering_mode == "reserved":
                # Use reserved number
                if not self.document_number_id:
                    raise UserError(_("Please select a reserved number."))
                if self.document_number_id.state != "reserved":
                    raise UserError(_("Selected number is not reserved."))
                # Mark as used
                self.document_number_id.write({
                    "state": "used",
                    "document_id": self.id,
                    "used_date": fields.Datetime.now(),
                })
                return self.document_sequence_id.format_number(self.document_number_id.number)

            elif self.numbering_mode == "available":
                # Use available (gap) number
                if not self.document_number_id:
                    raise UserError(_("Please select an available number."))
                # Use the number
                self.document_sequence_id.use_number(
                    self.document_number_id.number, self.id
                )
                return self.document_sequence_id.format_number(self.document_number_id.number)

            elif self.numbering_mode == "manual":
                # Use manually entered number
                if not self.manual_number:
                    raise UserError(_("Please enter a document number."))
                # Use the number
                self.document_sequence_id.use_number(self.manual_number, self.id)
                return self.document_sequence_id.format_number(self.manual_number)

            else:
                # Auto mode - use next available
                return self.document_sequence_id.get_next_and_use(self.id)

        # Fallback to document type sequence if available
        if self.document_type_id and self.document_type_id.sequence_id:
            return self.document_type_id.sequence_id.next_by_id()

        # Fallback to default sequence
        seq = self.env["ir.sequence"].next_by_code("sarabun.document") or "0001"

        return f"สจล./{seq}"

    def _activate_next_recipient(self):
        """Activate the next waiting recipient (sequential delivery)"""
        self.ensure_one()

        if self.state != "sent":
            return

        # Find next waiting recipient
        next_recipient = self.recipient_ids.filtered(
            lambda r: r.state == "waiting"
        ).sorted("sequence")[:1]

        if next_recipient:
            # Activate this recipient
            next_recipient.write({
                "state": "pending",
                "sent_date": fields.Datetime.now(),
            })
            next_recipient._send_notification()
        else:
            # No more waiting recipients - check if completed
            self._check_completion()

    def _check_completion(self):
        """Check if all recipients are done and update document state"""
        self.ensure_one()

        if self.state != "sent":
            return

        # Check for rejected recipients
        rejected = self.recipient_ids.filtered(lambda r: r.state == "rejected")
        if rejected:
            # Document stays in sent state, origin notified
            return

        # Check if all are completed (not waiting or pending)
        waiting_or_pending = self.recipient_ids.filtered(
            lambda r: r.state in ("waiting", "pending")
        )

        if not waiting_or_pending:
            self.state = "completed"
            self._on_routing_completed()

    def _mark_recipient_read(self):
        """Mark the current user's pending recipient as read"""
        self.ensure_one()
        user = self.env.user

        # Find pending recipients for current user
        for recipient in self.recipient_ids.filtered(lambda r: r.state == "pending"):
            if recipient._can_user_access(user):
                recipient.mark_as_read()

    def read(self, fields=None, load="_classic_read"):
        """Override to track read_date when document form is opened"""
        result = super().read(fields=fields, load=load)

        # Only track when reading full record (form view)
        # Avoid tracking when reading partial fields (list view)
        if fields is None or "subject" in fields:
            for record in self:
                if record.state == "sent":
                    record.sudo()._mark_recipient_read()

        return result

    def _on_routing_completed(self):
        """Called when all routing lines are completed"""
        self.message_post(
            body=_("All routing completed. Document is now complete."),
            message_type="notification",
        )

        # Callback to origin record if exists
        if self.origin_model and self.origin_res_id:
            try:
                origin_record = self.env[self.origin_model].browse(self.origin_res_id)
                if hasattr(origin_record, "_on_sarabun_completed"):
                    origin_record._on_sarabun_completed(self)
            except Exception:
                pass

    def _on_routing_rejected(self, recipient):
        """Called when a recipient rejects the document"""
        self.message_post(
            body=_("Document rejected by %s. Reason: %s")
            % (recipient.actioned_by.name, recipient.comment or _("No reason")),
            message_type="notification",
        )

        # Callback to origin record if exists
        if self.origin_model and self.origin_res_id:
            try:
                origin_record = self.env[self.origin_model].browse(self.origin_res_id)
                if hasattr(origin_record, "_on_sarabun_rejected"):
                    origin_record._on_sarabun_rejected(self, recipient)
            except Exception:
                pass

    # === Constraints ===
    @api.constrains("routing_line_ids")
    def _check_routing_lines(self):
        for record in self:
            approve_lines = record.routing_line_ids.filtered(
                lambda l: l.routing_type == "approve"
            )
            if len(approve_lines) > 1:
                # Allow multiple approvers but warn via tracking
                pass
