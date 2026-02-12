# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

ROUTING_TYPE_SEQUENCE= {
    "acknowledge": 10,
    "approve": 100,
}

class SarabunRoutingLine(models.Model):
    """
    Route definition - defines WHO should receive the document.
    This is just a "plan" or "template" for routing - no state tracking.
    State tracking is done in sarabun.document.recipient.
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

    # === Status from Recipient (for display) ===
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
        return super().create(vals_list)
    
    def write(self, vals):
        if 'routing_type' in vals and not vals.get('sequence'):
            vals['sequence'] = ROUTING_TYPE_SEQUENCE.get(vals['routing_type'], 10)
        return super().write(vals)

    # === Computed Fields ===
    @api.depends("document_id.recipient_ids", "document_id.recipient_ids.state", "document_id.recipient_ids.routing_line_id")
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

    # === Constraints ===
    @api.constrains("recipient_type", "user_id", "department_id", "role_id")
    def _check_recipient(self):
        for record in self:
            if record.recipient_type == "user" and not record.user_id:
                raise UserError(_("Please select a user for user-type recipient."))
            if record.recipient_type == "department" and not record.department_id:
                raise UserError(_("Please select a department for routing."))
            if record.recipient_type == "role" and not record.role_id:
                raise UserError(_("Please select a role/position for role-type recipient."))
