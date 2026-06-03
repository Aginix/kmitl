from odoo import models


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    def activity_schedule(
        self, act_type_xmlid="", date_deadline=None, summary="", note="", **act_values
    ):
        """Allow scheduling an *unassigned* group Todo (ADR-0002).

        Core forces ``user_id`` to ``env.uid`` whenever it is falsy, so a Todo
        tagged with a Responsible Role (and no explicit user) would wrongly get
        a single owner. We let core create it, then clear ``user_id`` so the
        Todo surfaces only through the live role-in-unit resolution.

        ``mail.activity.create`` does not notify when ``user_id == env.user``
        and skips assignation checks for automated activities, so resetting the
        user here raises no spurious notification.
        """
        is_group = bool(act_values.get("responsible_role_id")) and not act_values.get(
            "user_id"
        )
        activities = super().activity_schedule(
            act_type_xmlid=act_type_xmlid,
            date_deadline=date_deadline,
            summary=summary,
            note=note,
            **act_values,
        )
        if is_group:
            activities.sudo().write({"user_id": False})
        return activities
