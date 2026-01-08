# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SarabunDocumentSequence(models.Model):
    """
    Configurable document numbering sequence.
    Each sequence can be assigned to specific departments or shared across all.
    """

    _name = "sarabun.document.sequence"
    _description = "Sarabun Document Sequence"
    _order = "name"

    name = fields.Char(
        string="Sequence Name",
        required=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        help="Unique code for this sequence",
    )
    active = fields.Boolean(default=True)
    prefix = fields.Char(
        string="Prefix",
        help="Prefix for document numbers (e.g., 'สจล.', 'อว 6801.')",
    )
    suffix = fields.Char(
        string="Suffix",
        help="Suffix for document numbers",
    )
    padding = fields.Integer(
        string="Number Padding",
        default=4,
        help="Number of digits (e.g., 4 = 0001)",
    )
    reset_period = fields.Selection(
        selection=[
            ("never", "Never"),
            ("yearly", "Every Year"),
            ("fiscal_year", "Every Fiscal Year"),
        ],
        string="Reset Period",
        default="yearly",
        required=True,
    )
    current_year = fields.Integer(
        string="Current Year",
        default=lambda self: fields.Date.today().year,
    )

    # Department assignment
    department_ids = fields.Many2many(
        comodel_name="hr.department",
        relation="sarabun_sequence_department_rel",
        column1="sequence_id",
        column2="department_id",
        string="Departments",
        help="Leave empty to allow all departments to use this sequence",
    )
    is_shared = fields.Boolean(
        string="Shared Sequence",
        compute="_compute_is_shared",
        store=True,
    )

    # Document type assignment
    document_type_ids = fields.Many2many(
        comodel_name="sarabun.document.type",
        relation="sarabun_sequence_doctype_rel",
        column1="sequence_id",
        column2="document_type_id",
        string="Document Types",
        help="Leave empty to allow all document types",
    )

    # Related numbers
    number_ids = fields.One2many(
        comodel_name="sarabun.document.number",
        inverse_name="sequence_id",
        string="Numbers",
    )

    # Statistics
    next_number = fields.Integer(
        string="Next Number",
        compute="_compute_next_number",
    )
    reserved_count = fields.Integer(
        string="Reserved Count",
        compute="_compute_number_stats",
    )
    used_count = fields.Integer(
        string="Used Count",
        compute="_compute_number_stats",
    )

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Sequence code must be unique!"),
    ]

    @api.depends("department_ids")
    def _compute_is_shared(self):
        for record in self:
            record.is_shared = len(record.department_ids) == 0

    @api.depends("number_ids", "number_ids.state")
    def _compute_next_number(self):
        for record in self:
            used_numbers = record.number_ids.filtered(
                lambda n: n.state in ("used", "reserved") and n.year == record.current_year
            ).mapped("number")
            if used_numbers:
                record.next_number = max(used_numbers) + 1
            else:
                record.next_number = 1

    @api.depends("number_ids", "number_ids.state")
    def _compute_number_stats(self):
        for record in self:
            current_year_numbers = record.number_ids.filtered(
                lambda n: n.year == record.current_year
            )
            record.reserved_count = len(
                current_year_numbers.filtered(lambda n: n.state == "reserved")
            )
            record.used_count = len(
                current_year_numbers.filtered(lambda n: n.state == "used")
            )

    def _check_year_reset(self):
        """Check if year has changed and reset if needed"""
        self.ensure_one()
        current_year = fields.Date.today().year
        if self.reset_period == "yearly" and self.current_year != current_year:
            self.current_year = current_year

    def get_next_number(self):
        """Get the next available number"""
        self.ensure_one()
        self._check_year_reset()
        return self.next_number

    def get_available_numbers(self, limit=20):
        """Get list of available (gap) numbers"""
        self.ensure_one()
        self._check_year_reset()

        used_numbers = set(
            self.number_ids.filtered(
                lambda n: n.state in ("used", "reserved") and n.year == self.current_year
            ).mapped("number")
        )

        if not used_numbers:
            return list(range(1, limit + 1))

        max_used = max(used_numbers)
        all_numbers = set(range(1, max_used + 1))
        available = sorted(all_numbers - used_numbers)

        return available[:limit]

    def reserve_number(self, number, user_id=None, note=None):
        """Reserve a specific number"""
        self.ensure_one()
        self._check_year_reset()

        # Check if number is already used or reserved
        existing = self.number_ids.filtered(
            lambda n: n.number == number and n.year == self.current_year
        )
        if existing:
            if existing.state == "used":
                raise UserError(_("Number %s is already used.") % number)
            elif existing.state == "reserved":
                raise UserError(
                    _("Number %s is already reserved by %s.")
                    % (number, existing.reserved_by_id.name)
                )

        # Create reservation
        return self.env["sarabun.document.number"].create(
            {
                "sequence_id": self.id,
                "number": number,
                "year": self.current_year,
                "state": "reserved",
                "reserved_by_id": user_id or self.env.user.id,
                "reserved_date": fields.Datetime.now(),
                "note": note,
            }
        )

    def use_number(self, number, document_id):
        """Mark a number as used by a document"""
        self.ensure_one()
        self._check_year_reset()

        existing = self.number_ids.filtered(
            lambda n: n.number == number and n.year == self.current_year
        )

        if existing:
            if existing.state == "used":
                raise UserError(_("Number %s is already used.") % number)
            # Use reserved number
            existing.write(
                {
                    "state": "used",
                    "document_id": document_id,
                    "used_date": fields.Datetime.now(),
                }
            )
            return existing
        else:
            # Create new used number
            return self.env["sarabun.document.number"].create(
                {
                    "sequence_id": self.id,
                    "number": number,
                    "year": self.current_year,
                    "state": "used",
                    "document_id": document_id,
                    "used_date": fields.Datetime.now(),
                }
            )

    def format_number(self, number):
        """Format number with prefix/suffix"""
        self.ensure_one()
        formatted = str(number).zfill(self.padding)

        parts = []
        if self.prefix:
            parts.append(self.prefix)
        parts.append(formatted)
        if self.suffix:
            parts.append(self.suffix)

        return "".join(parts)

    def get_next_and_use(self, document_id):
        """Get next number and mark as used in one step"""
        self.ensure_one()
        next_num = self.get_next_number()
        self.use_number(next_num, document_id)
        return self.format_number(next_num)

    def action_view_numbers(self):
        """View all used numbers"""
        self.ensure_one()
        return {
            "name": _("Used Numbers"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document.number",
            "view_mode": "tree,form",
            "domain": [("sequence_id", "=", self.id), ("state", "=", "used")],
            "context": {"default_sequence_id": self.id},
        }

    def action_view_reserved(self):
        """View all reserved numbers"""
        self.ensure_one()
        return {
            "name": _("Reserved Numbers"),
            "type": "ir.actions.act_window",
            "res_model": "sarabun.document.number",
            "view_mode": "tree,form",
            "domain": [("sequence_id", "=", self.id), ("state", "=", "reserved")],
            "context": {"default_sequence_id": self.id},
        }


class SarabunDocumentNumber(models.Model):
    """
    Individual document numbers - tracks reserved, used, and available numbers.
    """

    _name = "sarabun.document.number"
    _description = "Sarabun Document Number"
    _order = "year desc, number desc"
    _rec_name = "display_name"

    sequence_id = fields.Many2one(
        comodel_name="sarabun.document.sequence",
        string="Sequence",
        required=True,
        ondelete="cascade",
        index=True,
    )
    number = fields.Integer(
        string="Number",
        required=True,
        index=True,
    )
    year = fields.Integer(
        string="Year",
        required=True,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("reserved", "Reserved"),
            ("used", "Used"),
            ("cancelled", "Cancelled"),
        ],
        string="State",
        default="reserved",
        required=True,
    )

    # Reservation info
    reserved_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Reserved By",
    )
    reserved_date = fields.Datetime(
        string="Reserved Date",
    )
    note = fields.Text(
        string="Note",
        help="Reason for reservation",
    )

    # Usage info
    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        ondelete="set null",
    )
    used_date = fields.Datetime(
        string="Used Date",
    )

    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )
    formatted_number = fields.Char(
        compute="_compute_formatted_number",
    )

    _sql_constraints = [
        (
            "number_year_sequence_uniq",
            "unique(sequence_id, number, year)",
            "Number must be unique per sequence per year!",
        ),
    ]

    @api.depends("sequence_id", "number", "year")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.sequence_id.code}/{record.year}/{record.number}"

    @api.depends("sequence_id", "number")
    def _compute_formatted_number(self):
        for record in self:
            if record.sequence_id:
                record.formatted_number = record.sequence_id.format_number(record.number)
            else:
                record.formatted_number = str(record.number)

    def action_cancel_reservation(self):
        """Cancel a reservation"""
        for record in self:
            if record.state != "reserved":
                raise UserError(_("Only reserved numbers can be cancelled."))
            record.state = "cancelled"

    def action_release(self):
        """Release a used number (make it available again)"""
        for record in self:
            if record.state != "used":
                raise UserError(_("Only used numbers can be released."))
            if record.document_id:
                raise UserError(
                    _("Cannot release number still linked to document %s.")
                    % record.document_id.name
                )
            record.unlink()
