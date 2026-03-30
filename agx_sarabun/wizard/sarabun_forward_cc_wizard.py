# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class SarabunForwardCCWizard(models.TransientModel):
    _name = "sarabun.forward.cc.wizard"
    _description = "Forward Document CC Wizard"

    document_id = fields.Many2one(
        comodel_name="sarabun.document",
        string="Document",
        required=True,
    )
    recipient_type = fields.Selection(
        selection=[
            ("user", "User"),
            ("department", "Department"),
            ("role", "Role/Position"),
        ],
        string="Forward To",
        required=True,
        default="user",
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Users",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
    )
    role_id = fields.Many2one(
        comodel_name="sarabun.role",
        string="Role/Position",
    )
    comment = fields.Text(string="Comment")

    def action_forward_cc(self):
        """Create CC recipient records."""
        self.ensure_one()
        if self.recipient_type == "user" and not self.user_ids:
            raise UserError(_("Please select at least one user to forward to."))
        if self.recipient_type == "department" and not self.department_id:
            raise UserError(_("Please select a department to forward to."))
        if self.recipient_type == "role" and not self.role_id:
            raise UserError(_("Please select a role to forward to."))

        Recipient = self.env["sarabun.document.recipient"].sudo()
        base_vals = {
            "document_id": self.document_id.id,
            "is_cc": True,
            "forwarded_by_user_id": self.env.user.id,
            "forward_comment": self.comment,
            "routing_type": "acknowledge",
            "state": "new",
        }

        if self.recipient_type == "user":
            for user in self.user_ids:
                vals = dict(
                    base_vals,
                    recipient_type="user",
                    user_id=user.id,
                )
                recipient = Recipient.create(vals)
                recipient._send_notification()
        elif self.recipient_type == "department":
            vals = dict(
                base_vals,
                recipient_type="department",
                department_id=self.department_id.id,
                department_text=self.department_id.name,
            )
            recipient = Recipient.create(vals)
            recipient._send_notification()
        elif self.recipient_type == "role":
            vals = dict(
                base_vals,
                recipient_type="role",
                role_id=self.role_id.id,
            )
            recipient = Recipient.create(vals)
            recipient._send_notification()

        return {"type": "ir.actions.act_window_close"}
