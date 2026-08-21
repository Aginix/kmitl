from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    is_own_only_user = fields.Boolean(
        compute="_compute_is_own_only_user",
        help="True when the acting user may only handle their own requests: a "
        "member of group_approval_own that is NOT a full Approval User "
        "(User implies Own, so the two must be distinguished this way).",
    )

    @api.depends_context("uid")
    def _compute_is_own_only_user(self):
        user = self.env.user
        own_only = user.has_group(
            "agx_approval_own_security.group_approval_own"
        ) and not user.has_group("agx_approval.group_approval_user")
        for rec in self:
            rec.is_own_only_user = own_only

    @api.constrains("owner_id")
    def _check_owner_is_self_for_own_group(self):
        """"Own only" users may file requests in their own name only: the
        requester (ผู้ขออนุมัติ) must be themselves. Full Users, Managers and
        superuser are unaffected."""
        if self.env.su:
            return
        user = self.env.user
        if not user.has_group(
            "agx_approval_own_security.group_approval_own"
        ) or user.has_group("agx_approval.group_approval_user"):
            return
        for rec in self:
            if rec.owner_id != user.employee_id:
                raise ValidationError(
                    _("You can only submit approval requests in your own name.")
                )
