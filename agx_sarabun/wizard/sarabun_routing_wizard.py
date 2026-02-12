# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SarabunRoutingLineWizard(models.TransientModel):
    """Wizard for adding/editing routing lines"""

    _name = "sarabun.routing.line.wizard"
    _description = "Routing Line Wizard"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
    )
    routing_line_id = fields.Many2one(
        comodel_name="sarabun.routing.line",
        string="Routing Line",
        help="If set, we're editing an existing line",
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
    role_id = fields.Many2one(
        comodel_name="sarabun.role",
        string="Role/Position",
    )

    @api.onchange("routing_line_id")
    def _onchange_routing_line_id(self):
        """Load values from existing routing line"""
        if self.routing_line_id:
            self.routing_type = self.routing_line_id.routing_type
            self.recipient_type = self.routing_line_id.recipient_type
            self.user_id = self.routing_line_id.user_id
            self.department_id = self.routing_line_id.department_id
            self.role_id = self.routing_line_id.role_id

    def action_confirm(self):
        """Create or update routing line"""
        self.ensure_one()

        # Validate recipient based on type
        if self.recipient_type == "user" and not self.user_id:
            raise UserError(_("Please select a user."))
        if self.recipient_type == "department" and not self.department_id:
            raise UserError(_("Please select a department."))
        if self.recipient_type == "role" and not self.role_id:
            raise UserError(_("Please select a role/position."))

        vals = {
            "routing_type": self.routing_type,
            "recipient_type": self.recipient_type,
            "user_id": self.user_id.id if self.user_id else False,
            "department_id": self.department_id.id if self.department_id else False,
            "role_id": self.role_id.id if self.role_id else False,
        }

        if self.routing_line_id:
            # Update existing line
            self.routing_line_id.write(vals)
        else:
            # Create new line
            vals["document_id"] = self.document_id.id
            self.env["sarabun.routing.line"].create(vals)

        return {"type": "ir.actions.act_window_close"}


class SarabunRoutingRejectWizard(models.TransientModel):
    _name = "sarabun.routing.reject.wizard"
    _description = "Reject Document Wizard"

    routing_line_id = fields.Many2one(
        comodel_name="sarabun.routing.line",
        string="Routing Line",
        required=True,
    )
    comment = fields.Text(
        string="Rejection Reason",
        required=True,
    )

    def action_reject(self):
        """Confirm rejection with comment"""
        self.ensure_one()
        if not self.comment:
            raise UserError(_("Please provide a rejection reason."))

        self.routing_line_id.action_do_reject(self.comment)
        return {"type": "ir.actions.act_window_close"}


class SarabunRoutingForwardWizard(models.TransientModel):
    _name = "sarabun.routing.forward.wizard"
    _description = "Forward Document Wizard"

    routing_line_id = fields.Many2one(
        comodel_name="sarabun.routing.line",
        string="Routing Line",
        required=True,
    )
    forward_type = fields.Selection(
        selection=[
            ("user", "User"),
            ("department", "Department"),
        ],
        string="Forward To",
        required=True,
        default="user",
    )
    forward_to_user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
    )
    forward_to_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
    )
    comment = fields.Text(
        string="Comment",
    )

    def action_forward(self):
        """Confirm forward"""
        self.ensure_one()
        if self.forward_type == "user" and not self.forward_to_user_id:
            raise UserError(_("Please select a user to forward to."))
        if self.forward_type == "department" and not self.forward_to_department_id:
            raise UserError(_("Please select a department to forward to."))

        self.routing_line_id.action_do_forward(
            forward_to_user_id=self.forward_to_user_id.id if self.forward_to_user_id else False,
            forward_to_department_id=self.forward_to_department_id.id if self.forward_to_department_id else False,
            comment=self.comment,
        )
        return {"type": "ir.actions.act_window_close"}


class SarabunDepartmentLookupWizard(models.TransientModel):
    """Wizard to search and select department, then insert text into target field"""

    _name = "sarabun.department.lookup.wizard"
    _description = "Department Lookup Wizard"

    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        required=True,
    )
    target_model = fields.Char(string="Target Model")
    target_record_id = fields.Integer(string="Target Record ID")
    target_field = fields.Char(string="Target Field")

    def action_select(self):
        """Insert selected department name into target field"""
        self.ensure_one()
        if self.target_model and self.target_record_id and self.target_field:
            record = self.env[self.target_model].browse(self.target_record_id)
            if record.exists():
                record.write({self.target_field: self.department_id.name})
        return {"type": "ir.actions.act_window_close"}


class SarabunRecipientRejectWizard(models.TransientModel):
    """Reject wizard for document recipient"""

    _name = "sarabun.recipient.reject.wizard"
    _description = "Reject Document Wizard (Recipient)"

    recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Recipient",
        required=True,
    )
    comment = fields.Text(
        string="Rejection Reason",
        required=True,
    )

    def action_reject(self):
        """Confirm rejection with comment"""
        self.ensure_one()
        if not self.comment:
            raise UserError(_("Please provide a rejection reason."))

        self.recipient_id.action_do_reject(self.comment)
        return {"type": "ir.actions.act_window_close"}


class SarabunNumberSelectionWizard(models.TransientModel):
    """Wizard to select document number (reserved, available, or manual)"""

    _name = "sarabun.number.selection.wizard"
    _description = "Document Number Selection Wizard"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
    )
    sequence_id = fields.Many2one(
        comodel_name="sarabun.document.sequence",
        string="Sequence",
        required=True,
    )
    selection_mode = fields.Selection(
        selection=[
            ("reserved", "Use Reserved Number"),
            ("available", "Use Available (Gap) Number"),
            ("manual", "Enter Manually"),
        ],
        string="Selection Mode",
        default="reserved",
        required=True,
    )

    # Reserved number selection
    reserved_number_id = fields.Many2one(
        comodel_name="sarabun.document.number",
        string="Reserved Number",
        domain="[('sequence_id', '=', sequence_id), ('state', '=', 'reserved')]",
    )

    # Available numbers display
    available_number_ids = fields.Many2many(
        comodel_name="sarabun.document.number",
        string="Available Numbers",
        compute="_compute_available_numbers",
    )
    selected_available_number = fields.Integer(
        string="Selected Available Number",
    )

    # Manual entry
    manual_number = fields.Integer(
        string="Manual Number",
    )

    # Display info
    next_auto_number = fields.Integer(
        string="Next Auto Number",
        compute="_compute_next_auto_number",
    )
    formatted_preview = fields.Char(
        string="Preview",
        compute="_compute_formatted_preview",
    )

    @api.depends("sequence_id")
    def _compute_next_auto_number(self):
        for record in self:
            if record.sequence_id:
                record.next_auto_number = record.sequence_id.get_next_number()
            else:
                record.next_auto_number = 0

    @api.depends("sequence_id")
    def _compute_available_numbers(self):
        """Get available (gap) numbers as virtual records"""
        for record in self:
            if record.sequence_id:
                available = record.sequence_id.get_available_numbers(limit=20)
                # Create temporary records for display
                Number = self.env["sarabun.document.number"]
                record.available_number_ids = Number
            else:
                record.available_number_ids = False

    @api.depends("selection_mode", "reserved_number_id", "selected_available_number", "manual_number", "sequence_id")
    def _compute_formatted_preview(self):
        for record in self:
            number = 0
            if record.selection_mode == "reserved" and record.reserved_number_id:
                number = record.reserved_number_id.number
            elif record.selection_mode == "available" and record.selected_available_number:
                number = record.selected_available_number
            elif record.selection_mode == "manual" and record.manual_number:
                number = record.manual_number

            if number and record.sequence_id:
                record.formatted_preview = record.sequence_id.format_number(number)
            else:
                record.formatted_preview = ""

    def action_confirm(self):
        """Confirm number selection and update document"""
        self.ensure_one()

        if self.selection_mode == "reserved":
            if not self.reserved_number_id:
                raise UserError(_("Please select a reserved number."))
            self.document_id.write({
                "numbering_mode": "reserved",
                "document_number_id": self.reserved_number_id.id,
            })

        elif self.selection_mode == "available":
            if not self.selected_available_number:
                raise UserError(_("Please select an available number."))
            # Create a temporary reserved number for the available slot
            number_record = self.sequence_id.reserve_number(
                self.selected_available_number,
                user_id=self.env.user.id,
                note=_("Reserved via number selection wizard for document")
            )
            self.document_id.write({
                "numbering_mode": "available",
                "document_number_id": number_record.id,
            })

        elif self.selection_mode == "manual":
            if not self.manual_number:
                raise UserError(_("Please enter a number."))
            # Validate the number is available
            existing = self.sequence_id.number_ids.filtered(
                lambda n: n.number == self.manual_number
                and n.year == self.sequence_id.current_year
                and n.state in ("used", "reserved")
            )
            if existing:
                if existing.state == "used":
                    raise UserError(_("Number %s is already used.") % self.manual_number)
                else:
                    raise UserError(_("Number %s is already reserved.") % self.manual_number)
            self.document_id.write({
                "numbering_mode": "manual",
                "manual_number": self.manual_number,
            })

        return {"type": "ir.actions.act_window_close"}

    def action_reserve_number(self):
        """Reserve a new number for later use"""
        self.ensure_one()
        if not self.manual_number:
            raise UserError(_("Please enter a number to reserve."))

        number_record = self.sequence_id.reserve_number(
            self.manual_number,
            user_id=self.env.user.id,
            note=_("Reserved via wizard")
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Number Reserved"),
                "message": _("Number %s has been reserved.") % self.sequence_id.format_number(self.manual_number),
                "type": "success",
                "sticky": False,
            },
        }
