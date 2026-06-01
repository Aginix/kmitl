# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

READONLY_STATES = {
    "sent": [("readonly", True)],
    "completed": [("readonly", True)],
    "cancelled": [("readonly", True)],
}


class SarabunDocument(models.Model):
    _name = "sarabun.document"
    _description = "Sarabun Document"
    _inherit = ["mail.thread", "mail.activity.mixin", "portal.mixin", 'thai.date.mixin']
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
        related="sender_department_id.complete_name",
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

    # === Report Delegation ===
    has_delegated_report = fields.Boolean(
        compute="_compute_delegated_report",
        string="Has Delegated Report",
    )
    delegated_report_url = fields.Char(
        compute="_compute_delegated_report",
        string="Report Preview URL",
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

    can_edit = fields.Boolean(compute="_compute_can_edit")

    @api.depends("state")
    def _compute_can_edit(self):
        for rec in self:
            rec.can_edit = rec.state == "draft"

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

    # === Current User Inbox ===
    current_user_inbox_is_read = fields.Boolean(
        compute="_compute_current_user_inbox_is_read",
    )

    # === Current User Action ===
    current_user_recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        compute="_compute_current_user_recipient",
        string="My Pending Action",
    )
    current_user_can_acknowledge = fields.Boolean(
        compute="_compute_current_user_recipient",
    )
    current_user_can_approve = fields.Boolean(
        compute="_compute_current_user_recipient",
    )
    report_preview_url = fields.Char(
        compute="_compute_report_preview_url",
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
    attachment_ids = fields.One2many(
        "ir.attachment",
        "res_id",
        domain=[("res_model", "=", "sarabun.document")],
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

    @api.depends("origin_model", "origin_res_id")
    def _compute_delegated_report(self):
        for record in self:
            delegated_report = record._get_delegated_report_action()
            record.has_delegated_report = bool(delegated_report)

            # Compute report URL for iframe preview
            if delegated_report and record.origin_model and record.origin_res_id:
                try:
                    origin = record.env[record.origin_model].browse(record.origin_res_id)
                    if origin.exists() and hasattr(origin, "get_portal_url"):
                        record.delegated_report_url = origin.get_portal_url(report_type="html")
                    else:
                        record.delegated_report_url = False
                except Exception:
                    record.delegated_report_url = False
            else:
                record.delegated_report_url = False

    @api.depends("recipient_ids", "recipient_ids.state", "routing_line_ids")
    def _compute_routing_progress(self):
        for record in self:
            total = len(record.routing_line_ids)
            if total:
                done = len(
                    record.recipient_ids.filtered(
                        lambda r: r.state in ("acknowledged", "approved")
                    )
                )
                record.routing_progress = (done / total) * 100
            else:
                record.routing_progress = 0

    @api.depends("recipient_ids", "recipient_ids.state")
    def _compute_routing_counts(self):
        for record in self:
            record.pending_routing_count = len(
                record.recipient_ids.filtered(lambda r: r.state == "new")
            )
            record.completed_routing_count = len(
                record.recipient_ids.filtered(
                    lambda r: r.state in ("acknowledged", "approved")
                )
            )

    @api.depends("recipient_ids", "recipient_ids.state")
    def _compute_current_user_recipient(self):
        for record in self:
            recipient = False
            for r in record.recipient_ids.filtered(lambda x: x.state == "new"):
                if r._can_user_access():
                    recipient = r
                    break
            record.current_user_recipient_id = recipient
            record.current_user_can_acknowledge = (
                bool(recipient) and recipient.routing_type == "acknowledge"
            )
            record.current_user_can_approve = (
                bool(recipient) and recipient.routing_type == "approve"
            )

    def _compute_current_user_inbox_is_read(self):
        for record in self:
            inbox = self.env["sarabun.inbox"].search([
                ("user_id", "=", self.env.user.id),
                ("document_id", "=", record.id),
            ], limit=1)
            record.current_user_inbox_is_read = inbox.is_read if inbox else True

    def action_mark_inbox_read(self):
        """Mark inbox as read for current user"""
        self.ensure_one()
        inbox_entries = self.env["sarabun.inbox"].search([
            ("user_id", "=", self.env.user.id),
            ("document_id", "=", self.id),
            ("is_read", "=", False),
        ])
        if inbox_entries:
            inbox_entries.action_mark_read()

    def action_mark_inbox_unread(self):
        """Mark inbox as unread for current user"""
        self.ensure_one()
        inbox_entries = self.env["sarabun.inbox"].search([
            ("user_id", "=", self.env.user.id),
            ("document_id", "=", self.id),
            ("is_read", "=", True),
        ])
        if inbox_entries:
            inbox_entries.action_mark_unread()

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

    # === Actions ===
    def action_send(self):
        """Send document and create recipients from routing lines"""
        for document in self:
            if document.state != "draft":
                raise UserError(_("Only draft documents can be sent."))

            if not document.routing_line_ids:
                raise UserError(_("Please add at least one routing line."))
            
            if not document.recipient:
                raise UserError(_("กรุณาระบุผู้รับก่อนยืนยันเอกสาร"))
            
            # # === VALIDATE ROUTING ORDER BEFORE SENDING ===
            lines = document.routing_line_ids.sorted("sequence")
            approve_lines = lines.filtered(lambda l: l.routing_type == "approve")

            if approve_lines:
                max_seq = max(lines.mapped("sequence"))
                for approve_line in approve_lines:
                    if approve_line.sequence < max_seq:
                        raise ValidationError(
                            _("Cannot send document: All approval steps must be at the end of routing. "
                            "Please reorder your routing lines.")
                        )
            # # === END VALIDATION ===

            # Generate document number
            if document.name == "/":
                document.name = document._generate_document_number()

            document.state = "sent"

            # Create only the first recipient (not all at once)
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

    def action_acknowledge(self):
        """Acknowledge - delegate to current recipient"""
        self.ensure_one()
        if not self.current_user_recipient_id:
            raise UserError(_("No pending action for you."))
        return self.current_user_recipient_id.action_acknowledge()

    def action_approve(self):
        """Approve - delegate to current recipient"""
        self.ensure_one()
        if not self.current_user_recipient_id:
            raise UserError(_("No pending action for you."))
        return self.current_user_recipient_id.action_approve()

    def action_reject(self):
        """Reject - delegate to current recipient"""
        self.ensure_one()
        if not self.current_user_recipient_id:
            raise UserError(_("No pending action for you."))
        return self.current_user_recipient_id.action_reject()

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

    def action_select_route(self):
        """Open wizard to select route template when multiple match"""
        self.ensure_one()
        templates = self._get_matching_route_templates()

        if not templates:
            raise UserError(_("No route templates available for this document."))

        if len(templates) == 1:
            # Only one template, apply directly
            self._apply_route_template(templates)
            return True

        # Multiple templates, open selection wizard
        return {
            "name": _("Select Route"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.route.selection.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_document_id": self.id,
                "default_available_template_ids": [(6, 0, templates.ids)],
            },
        }

    def _get_matching_route_templates(self):
        """Get route templates that match this document's context"""
        self.ensure_one()

        origin_record = False
        if self.origin_model and self.origin_res_id:
            try:
                origin_record = self.env[self.origin_model].browse(self.origin_res_id)
                if not origin_record.exists():
                    origin_record = False
            except Exception:
                origin_record = False

        return self.env["sarabun.route.template"].find_matching_templates(
            origin_record=origin_record,
            department_id=self.sender_department_id.id if self.sender_department_id else False,
            document_type_id=self.document_type_id.id if self.document_type_id else False,
        )

    def _apply_route_template(self, template):
        """Apply route template to this document"""
        self.ensure_one()
        self.route_template_id = template
        # Create routing lines from template
        lines = []
        for tmpl_line in template.line_ids:
            line_vals = {
                "sequence": tmpl_line.sequence,
                "routing_type": tmpl_line.routing_type,
                "recipient_type": tmpl_line.recipient_type,
                "user_id": tmpl_line.user_id.id if tmpl_line.user_id else False,
                "department_id": tmpl_line.department_id.id if tmpl_line.department_id else False,
                "role_id": tmpl_line.role_id.id if tmpl_line.role_id else False,
            }
            lines.append((0, 0, line_vals))
        # Clear existing and set new
        self.routing_line_ids = [(5, 0, 0)] + lines

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
        """Create the next recipient from routing lines (sequential delivery)"""
        self.ensure_one()

        if self.state != "sent":
            return

        # Find which routing lines already have recipients
        existing_line_ids = self.recipient_ids.mapped("routing_line_id").ids

        # Find next routing line that doesn't have a recipient yet
        next_line = self.routing_line_ids.filtered(
            lambda l: l.id not in existing_line_ids
        ).sorted("sequence")[:1]

        if next_line:
            # Create new recipient (state=new)
            Recipient = self.env["sarabun.document.recipient"].sudo()
            new_recipient = Recipient.create({
                "document_id": self.id,
                "routing_line_id": next_line.id,
                "sequence": next_line.sequence,
                "routing_type": next_line.routing_type,
                "recipient_type": next_line.recipient_type,
                "user_id": next_line.user_id.id if next_line.user_id else False,
                "department_id": next_line.department_id.id if next_line.department_id else False,
                "department_text": next_line.department_text,
                "role_id": next_line.role_id.id if next_line.role_id else False,
                "state": "new",
            })
            new_recipient._send_notification()
        else:
            # No more routing lines - check if completed
            self._check_completion()

    def _check_completion(self):
        """Check if all routing lines are done and update document state"""
        self.ensure_one()

        if self.state != "sent":
            return

        # Check for rejected recipients
        rejected = self.recipient_ids.filtered(lambda r: r.state == "rejected")
        if rejected:
            # Document stays in sent state, origin notified
            return

        # Check if all routing lines have been processed
        # (recipient exists and state is not 'new')
        all_lines_count = len(self.routing_line_ids)
        completed_count = len(self.recipient_ids.filtered(
            lambda r: r.state in ("acknowledged", "approved")
        ))

        if completed_count >= all_lines_count:
            self.state = "completed"
            self._on_routing_completed()

    def _mark_recipient_read(self):
        """Mark the current user's new recipient as read"""
        self.ensure_one()
        user = self.env.user

        # Find new recipients for current user
        for recipient in self.recipient_ids.filtered(lambda r: r.state == "new"):
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
        # Use sudo() because the approver may not have access to the origin record
        if self.origin_model and self.origin_res_id:
            try:
                origin_record = self.env[self.origin_model].sudo().browse(self.origin_res_id)
                if origin_record.exists() and hasattr(origin_record, "_on_sarabun_completed"):
                    _logger.info(
                        "Calling _on_sarabun_completed on %s (id=%s)",
                        self.origin_model, self.origin_res_id
                    )
                    origin_record._on_sarabun_completed(self)
            except Exception as e:
                _logger.exception(
                    "Error calling _on_sarabun_completed for %s (id=%s): %s",
                    self.origin_model, self.origin_res_id, e
                )

    def _on_routing_rejected(self, recipient):
        """Called when a recipient rejects the document"""
        self.message_post(
            body=_("Document rejected by %s. Reason: %s")
            % (recipient.actioned_by.name, recipient.comment or _("No reason")),
            message_type="notification",
        )

        # Callback to origin record if exists
        # Use sudo() because the approver may not have access to the origin record
        if self.origin_model and self.origin_res_id:
            try:
                origin_record = self.env[self.origin_model].sudo().browse(self.origin_res_id)
                if origin_record.exists() and hasattr(origin_record, "_on_sarabun_rejected"):
                    _logger.info(
                        "Calling _on_sarabun_rejected on %s (id=%s)",
                        self.origin_model, self.origin_res_id
                    )
                    origin_record._on_sarabun_rejected(self, recipient)
            except Exception as e:
                _logger.exception(
                    "Error calling _on_sarabun_rejected for %s (id=%s): %s",
                    self.origin_model, self.origin_res_id, e
                )

    def _trigger_origin_action_callback(self, recipient, action):
        """Trigger _on_sarabun_action callback on origin record for every action"""
        self.ensure_one()
        if self.origin_model and self.origin_res_id:
            try:
                origin_record = self.env[self.origin_model].sudo().browse(self.origin_res_id)
                if origin_record.exists() and hasattr(origin_record, "_on_sarabun_action"):
                    _logger.info(
                        "Calling _on_sarabun_action on %s (id=%s) with action=%s",
                        self.origin_model, self.origin_res_id, action
                    )
                    origin_record._on_sarabun_action(self, recipient, action)
            except Exception as e:
                _logger.exception(
                    "Error calling _on_sarabun_action for %s (id=%s): %s",
                    self.origin_model, self.origin_res_id, e
                )

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

    # === Portal ===
    def _compute_access_url(self):
        """Compute the access URL for portal access."""
        super()._compute_access_url()
        for document in self:
            document.access_url = f"/my/sarabun_document/{document.id}"

    def _compute_report_preview_url(self):
        """Compute the preview URL for report preview."""
        for document in self:
            document.report_preview_url = document.get_portal_url(report_type='html')

    def _get_delegated_report_action(self):
        """Get report action from origin model if available for delegation"""
        self.ensure_one()
        if self.origin_model and self.origin_res_id:
            try:
                origin = self.env[self.origin_model].browse(self.origin_res_id)
                if origin.exists() and hasattr(origin, "_get_sarabun_report_action"):
                    return origin._get_sarabun_report_action()
            except Exception:
                pass
        return False

    def _get_report_base_filename(self):
        """Override to use origin filename when delegating report"""
        self.ensure_one()
        report_action = self._get_delegated_report_action()
        if report_action and self.origin_model and self.origin_res_id:
            try:
                origin = self.env[self.origin_model].browse(self.origin_res_id)
                if origin.exists():
                    if hasattr(origin, '_get_report_base_filename'):
                        return origin._get_report_base_filename()
                    return origin.display_name
            except Exception:
                pass
        return 'Sarabun Document-%s' % (self.name)

    def open_preview(self):
        if self.id:
            return {
                'type': 'ir.actions.act_url',
                'url': self.access_url,
                'target': 'new',
            }

    def action_print_report(self):
        """Print report - uses delegated report from origin if available"""
        self.ensure_one()
        delegated_report = self._get_delegated_report_action()
        if delegated_report and self.origin_model and self.origin_res_id:
            # Use origin model's report
            origin = self.env[self.origin_model].browse(self.origin_res_id)
            if origin.exists():
                return delegated_report.report_action(origin)
        # Fallback to Sarabun's own report
        return self.env.ref('agx_sarabun.action_report_sarabun_documents').report_action(self)
