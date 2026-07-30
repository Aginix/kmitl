# -*- coding: utf-8 -*-
from odoo import fields, models


GODMODE_GROUP = "purchase_request_approval_godmode.group_pa_godmode"


class PurchaseRequestApprovalLine(models.Model):
    _inherit = "purchase.request.approval.line"

    # Related helpers so the editable-tree `attrs` can reference the parent's
    # state and the current user's God Mode flag without a `parent.` prefix
    # (which is fragile inside inline-editable one2many trees).
    approval_state = fields.Selection(related="approval_id.state")
    approval_user_has_godmode = fields.Boolean(
        related="approval_id.user_has_godmode",
    )

    def write(self, vals):
        """God-Mode edits at the line level are silent (no chatter / no
        follower notification). PDF regeneration is triggered by the parent
        model's `write()` override because `line_ids` is a PDF-visible field
        on the PA.
        """
        if self.env.user.has_group(GODMODE_GROUP):
            silent_self = self.with_context(
                tracking_disable=True,
                mail_notrack=True,
                mail_create_nolog=True,
            )
            return super(PurchaseRequestApprovalLine, silent_self).write(vals)
        return super().write(vals)
