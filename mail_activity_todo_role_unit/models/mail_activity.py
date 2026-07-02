from odoo import fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    # --- Group routing tags: role-in-unit, resolved live (ADR-0002) ---
    responsible_role_id = fields.Many2one(
        "res.users.role",
        string="Responsible Role",
        index=True,
        ondelete="cascade",
        help="When set together with an Operating Unit, this is a group Todo for "
        "everyone holding this role in that unit. Leave empty for a personal Todo.",
    )
    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Operating Unit",
        index=True,
        ondelete="cascade",
    )
    # Group Todos have no single assignee (ADR-0002).
    user_id = fields.Many2one(required=False)

    def _my_todo_domain(self):
        """Extend the personal inbox domain (core) with group Todos for a role
        the user holds in one of their operating units — unclaimed, or claimed
        by this user. A group Todo claimed by someone else drops out (Claim)."""
        domain = super()._my_todo_domain()
        user = self.env.user
        role_ids = user.todo_role_ids.ids
        ou_ids = user.operating_unit_ids.ids
        if role_ids and ou_ids:
            return (
                ["|"]
                + domain
                + [
                    "&",
                    "&",
                    ("responsible_role_id", "in", role_ids),
                    ("operating_unit_id", "in", ou_ids),
                    ("user_id", "in", [False, user.id]),
                ]
            )
        return domain

    def _todo_recipient_partners(self):
        """Add the live role-in-unit members for group Todos (ADR-0002): never a
        stored list — resolved fresh from role ∩ operating unit."""
        partners = super()._todo_recipient_partners()
        for act in self:
            if (
                not act.user_id
                and act.responsible_role_id
                and act.operating_unit_id
            ):
                users = (
                    act.responsible_role_id.sudo().user_ids
                    & act.operating_unit_id.sudo().user_ids
                )
                partners |= users.partner_id
        return partners

    def action_claim(self):
        """รับเรื่อง — take an unclaimed group Todo as your own so colleagues
        see it is being handled (and it leaves their inbox)."""
        to_claim = self.filtered(lambda a: a.responsible_role_id and not a.user_id)
        # Resolve the group before claiming so every member's badge refreshes.
        partners = to_claim._todo_recipient_partners()
        to_claim.write({"user_id": self.env.uid})
        self._todo_notify(partners)
        return True

    def action_unclaim(self):
        """Release a claimed group Todo back to the role-in-unit."""
        to_release = self.filtered("responsible_role_id")
        to_release.write({"user_id": False})
        self._todo_notify(to_release._todo_recipient_partners())
        return True

    def action_reassign(self, user):
        """มอบหมายให้… — hand a group Todo to a specific user within role ∩ OU.

        Symmetric with ``action_claim``: caller is responsible for filtering the
        recordset to group Todos and enforcing the role ∩ OU domain on ``user``.
        Notifies both the pre-write recipients (whose inbox drops the Todo) and
        the new assignee (whose inbox picks it up).
        """
        to_reassign = self.filtered("responsible_role_id")
        partners_before = to_reassign._todo_recipient_partners()
        to_reassign.write({"user_id": user.id})
        self._todo_notify(partners_before | user.partner_id)
        return True

    def action_open_reassign_wizard(self):
        """Open the delegate wizard on the selected activities (Inbox entry point).

        The wizard also opens from a source record via
        ``todo.assignable.action_reassign_todo_on_record``; both paths funnel
        through the same wizard.
        """
        return {
            "type": "ir.actions.act_window",
            "name": "มอบหมายให้...",
            "res_model": "todo.assign.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "mail.activity",
                "active_ids": self.ids,
                "active_id": self.id if len(self) == 1 else False,
            },
        }
