# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SarabunSigningWizard(models.TransientModel):
    _name = "sarabun.signing.wizard"
    _description = "Sarabun Signing Position Wizard"

    # Support both routing_line (legacy) and recipient (new)
    routing_line_id = fields.Many2one(
        comodel_name="sarabun.routing.line",
        string="Routing Line",
    )
    recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Recipient",
    )
    action_type = fields.Selection(
        selection=[
            ("approve", "Approve"),
            ("acknowledge", "Acknowledge"),
        ],
        string="Action Type",
        required=True,
    )
    available_role_ids = fields.Many2many(
        comodel_name="sarabun.role",
        string="Available Roles",
        compute="_compute_available_roles",
    )
    selected_role_id = fields.Many2one(
        comodel_name="sarabun.role",
        string="Sign As",
        required=True,
        domain="[('id', 'in', available_role_ids)]",
    )

    # Display fields
    document_name = fields.Char(
        string="Document",
        compute="_compute_document_info",
    )
    document_subject = fields.Char(
        string="Subject",
        compute="_compute_document_info",
    )

    @api.depends("routing_line_id", "recipient_id")
    def _compute_document_info(self):
        for record in self:
            if record.recipient_id:
                record.document_name = record.recipient_id.document_id.name
                record.document_subject = record.recipient_id.document_id.subject
            elif record.routing_line_id:
                record.document_name = record.routing_line_id.document_id.name
                record.document_subject = record.routing_line_id.document_id.subject
            else:
                record.document_name = False
                record.document_subject = False

    @api.depends("routing_line_id", "recipient_id")
    def _compute_available_roles(self):
        for record in self:
            record.available_role_ids = self.env["sarabun.role"].get_user_roles()

    def action_confirm(self):
        """Confirm signing with selected role"""
        self.ensure_one()

        if not self.selected_role_id:
            raise UserError(_("Please select a signing position."))

        # Handle recipient (new model)
        if self.recipient_id:
            if self.action_type == "approve":
                self.recipient_id.action_do_approve(self.selected_role_id.id)
            elif self.action_type == "acknowledge":
                self.recipient_id.action_do_acknowledge(self.selected_role_id.id)
            else:
                raise UserError(_("Invalid action type."))
        # Handle routing_line (legacy)
        elif self.routing_line_id:
            if self.action_type == "approve":
                self.routing_line_id.action_do_approve(self.selected_role_id.id)
            elif self.action_type == "acknowledge":
                self.routing_line_id.action_do_acknowledge(self.selected_role_id.id)
            else:
                raise UserError(_("Invalid action type."))
        else:
            raise UserError(_("No routing line or recipient specified."))

        return {"type": "ir.actions.act_window_close"}
