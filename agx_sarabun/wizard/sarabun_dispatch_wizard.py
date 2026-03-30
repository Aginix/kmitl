# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class SarabunDispatchWizard(models.TransientModel):
    _name = "sarabun.dispatch.wizard"
    _description = "Dispatch Document Wizard"

    recipient_id = fields.Many2one(
        comodel_name="sarabun.document.recipient",
        string="Recipient",
        required=True,
    )
    dispatch_to_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Dispatch To (Optional)",
        help="Optionally specify exact user. "
        "If blank, original recipient target is used.",
    )
    note = fields.Text(string="Dispatch Note")

    def action_dispatch(self):
        """Dispatch document to actual recipient."""
        self.ensure_one()
        recipient = self.recipient_id
        if not recipient.needs_dispatch:
            raise UserError(_("This recipient does not need dispatch."))

        vals = {
            "needs_dispatch": False,
            "dispatched_by_user_id": self.env.user.id,
            "dispatched_date": fields.Datetime.now(),
            "dispatch_note": self.note,
            "is_notified": False,  # Reset so it re-notifies actual recipient
        }
        if self.dispatch_to_user_id:
            vals.update({
                "recipient_type": "user",
                "user_id": self.dispatch_to_user_id.id,
            })
        recipient.write(vals)
        recipient._send_notification()

        # Email dispatched recipient
        recipient.document_id._send_sarabun_email(
            recipient._get_users_to_notify(),
            "agx_sarabun.email_template_sarabun_dispatched",
        )

        recipient.document_id.message_post(
            body=_("Document dispatched by %s (Central Correspondence)%s")
            % (
                self.env.user.name,
                _(" to %s") % self.dispatch_to_user_id.name
                if self.dispatch_to_user_id
                else "",
            ),
            message_type="notification",
        )
        return {"type": "ir.actions.act_window_close"}
