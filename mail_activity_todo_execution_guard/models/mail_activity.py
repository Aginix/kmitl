from odoo import _, models
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.mail_activity_todo.models.mail_activity import (
    SOURCE_CLEARED_CATEGORY,
)

# mail.activity methods the web client calls directly to close an activity
# (chatter Mark Done / Upload Document / Cancel, activity form buttons).
MANUAL_CLOSE_METHODS = {
    "action_feedback",
    "action_feedback_schedule_next",
    "action_done",
    "action_done_schedule_next",
    "unlink",
}


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _todo_check_manual_close(self):
        """Refuse closing an Execution Todo straight from the client.

        Business code closes these inside its own RPC on the source model, so
        only a request whose top-level call is mail.activity itself is blocked.
        Admins may still clear stuck Todos.
        """
        if not request or self.env.su or self.env.user._is_system():
            return
        params = getattr(request, "params", None) or {}
        if (
            params.get("model") != self._name
            or params.get("method") not in MANUAL_CLOSE_METHODS
        ):
            return
        if any(a.todo_category == SOURCE_CLEARED_CATEGORY for a in self):
            raise UserError(
                _("This task can only be closed by acting on the source document.")
            )

    def action_feedback(self, feedback=False, attachment_ids=None):
        self._todo_check_manual_close()
        return super().action_feedback(feedback=feedback, attachment_ids=attachment_ids)

    def action_feedback_schedule_next(self, feedback=False, attachment_ids=None):
        self._todo_check_manual_close()
        return super().action_feedback_schedule_next(
            feedback=feedback, attachment_ids=attachment_ids
        )

    def action_done(self):
        self._todo_check_manual_close()
        return super().action_done()

    def action_done_schedule_next(self):
        self._todo_check_manual_close()
        return super().action_done_schedule_next()

    def unlink(self):
        self._todo_check_manual_close()
        return super().unlink()
