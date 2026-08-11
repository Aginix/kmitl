from odoo import api, fields, models


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

    # ------------------------------------------------------------------
    # Operating Unit is a cache of the *source record's* OU (ADR-0002).
    # Denormalised onto the activity so routing / history / group-by stay pure
    # SQL, and kept live by mail.activity.mixin.write (source OU change → the
    # open activities follow). Filled here at creation for every path — chatter
    # "Schedule Activity", the inbox form, and activity_schedule alike.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("operating_unit_id"):
                ou = self._source_operating_unit(vals)
                if ou:
                    vals["operating_unit_id"] = ou.id
        return super().create(vals_list)

    @api.model
    def _source_operating_unit(self, vals):
        """The operating unit of the source record these vals point at, when that
        model carries one — else an empty recordset. sudo: reading the source's
        OU is metadata resolution, independent of who schedules the activity."""
        res_id = vals.get("res_id")
        if not res_id:
            return self.env["operating.unit"]
        model = vals.get("res_model")
        if not model and vals.get("res_model_id"):
            model = self.env["ir.model"].sudo().browse(vals["res_model_id"]).model
        if not model or model not in self.env:
            return self.env["operating.unit"]
        source = self.env[model]
        if "operating_unit_id" not in source._fields:
            return self.env["operating.unit"]
        record = source.sudo().browse(res_id).exists()
        return record.operating_unit_id

    # ------------------------------------------------------------------
    # Group vs personal are mutually exclusive on the form (chatter "Schedule
    # Activity" popup + inbox form): a role routes to everyone holding it in the
    # OU (user_id empty), a single assignee routes to one person. The core popup
    # defaults user_id to the current user, so without this picking a role would
    # leave a stray assignee and the Todo would stay personal.
    # ------------------------------------------------------------------
    @api.onchange("responsible_role_id")
    def _onchange_responsible_role_id(self):
        """Pick a role → make it a group Todo: drop the single assignee and
        surface the source record's OU (also filled on save via create)."""
        if self.responsible_role_id:
            self.user_id = False
            if not self.operating_unit_id:
                self.operating_unit_id = self._source_operating_unit(
                    {
                        "res_model": self.res_model,
                        "res_model_id": self.res_model_id.id,
                        "res_id": self.res_id,
                    }
                )

    @api.onchange("user_id")
    def _onchange_user_id_clear_role(self):
        """Assign a person → make it personal: drop the group role."""
        if self.user_id:
            self.responsible_role_id = False

    def _my_todo_domain(self):
        """Extend the personal inbox domain (core) with group Todos for a role
        the user holds in one of their subscribed operating units — unclaimed, or
        claimed by this user. A group Todo claimed by someone else drops out (Claim).
        Uses todo_subscribed_operating_unit_ids (opt-in, defaults to assigned OUs)
        rather than operating_unit_ids (permission-based) so oversight users with
        wide OU access are not spammed by Todos from OUs they don't work in."""
        domain = super()._my_todo_domain()
        user = self.env.user
        role_ids = user.todo_role_ids.ids
        ou_ids = user.todo_subscribed_operating_unit_ids.ids
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
        stored list — resolved fresh from role ∩ operating unit, then filtered
        to users who have subscribed to that OU so oversight users with wide OU
        access don't receive inbox notifications for OUs they don't work in."""
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
                subscribed = users.filtered(
                    lambda u: act.operating_unit_id
                    in u.todo_subscribed_operating_unit_ids
                )
                partners |= subscribed.partner_id
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
