# -*- coding: utf-8 -*-
from odoo import _, fields, models


class SarabunDelegateWizard(models.TransientModel):
    _name = "sarabun.delegate.wizard"
    _description = "Delegate Action Wizard"

    recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Recipient",
        required=True,
    )
    delegate_to_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Delegate To",
        required=True,
    )
    comment = fields.Text(string="Comment")

    def action_delegate(self):
        """Create delegated recipient."""
        self.ensure_one()
        original = self.recipient_id
        Recipient = self.env["sarabun.document.recipient"].sudo()
        delegate = Recipient.create({
            "document_id": original.document_id.id,
            "routing_line_id": (
                original.routing_line_id.id if original.routing_line_id else False
            ),
            "sequence": original.sequence,
            "routing_type": original.routing_type,
            "recipient_type": "user",
            "user_id": self.delegate_to_user_id.id,
            "state": "new",
            "is_delegated": True,
            "delegated_by_user_id": self.env.user.id,
            "delegated_by_recipient_id": original.id,
        })
        delegate._send_notification()

        # Email delegate about delegation
        original.document_id._send_sarabun_email(
            self.delegate_to_user_id,
            "agx_sarabun.email_template_sarabun_delegated",
        )

        original.document_id.message_post(
            body=_("%s delegated action to %s")
            % (self.env.user.name, self.delegate_to_user_id.name),
            message_type="notification",
        )
        return {"type": "ir.actions.act_window_close"}
