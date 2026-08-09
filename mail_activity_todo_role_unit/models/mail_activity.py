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
