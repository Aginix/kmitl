# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    state = fields.Selection(
        selection_add=[("submitted", "Submitted"), ("posted",)],
        ondelete={"submitted": "set default"},
    )

    def action_submit(self):
        """Submit the journal entry for approval."""
        for move in self:
            if move.state != "draft":
                raise UserError(_("Only draft entries can be submitted."))
            move.state = "submitted"
        return True

    def action_draft(self):
        """Reset journal entry from submitted back to draft."""
        for move in self:
            if move.state != "submitted":
                raise UserError(_("Only submitted entries can be reset to draft."))
            move.state = "draft"
        return True
