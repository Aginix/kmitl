# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DisbursementAssignmentRule(models.Model):
    """Routing rule that maps a disbursement request to a responsible officer.

    When a request arrives at a station it is matched against the rules of that
    station (ordered by ``sequence``) and the first matching rule's officer is
    stored in ``disbursement.request.assigned_to``. A rule without a station
    applies to the first station of the route. Matching is advisory: it only
    pre-fills the responsible officer and raises a To-Do; it never locks who
    may act on the request.
    """

    _name = "disbursement.assignment.rule"
    _description = "Disbursement Assignment Rule"
    _order = "sequence, id"
    _rec_name = "user_id"

    # Dimension criteria used for matching, in stored-field order. An empty
    # criterion behaves as a wildcard (matches any value on that dimension).
    _CRITERIA = (
        "department_analytic_id",
        "source_analytic_id",
        "fund_analytic_id",
        "activity_analytic_id",
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # -- criteria: empty = wildcard --------------------------------------
    # ``ondelete="restrict"`` prevents a rule from silently turning into a
    # wildcard when the referenced analytic account / partner type is removed.
    department_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Department",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "departments")],
    )
    source_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Source",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "sources")],
    )
    fund_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Fund",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "funds")],
    )
    activity_analytic_id = fields.Many2one(
        "account.analytic.account",
        string="Activity",
        ondelete="restrict",
        domain=[("root_plan_id.code", "=", "activities")],
    )
    partner_type_id = fields.Many2one(
        "res.partner.type",
        string="Partner Type",
        ondelete="restrict",
    )

    work_center_id = fields.Many2one(
        "work.center",
        string="Station",
        ondelete="restrict",
        domain=lambda self: [
            ("area_id.model_ids.model", "=", "disbursement.request"),
            ("is_unassigned", "=", False),
        ],
        help="Station where this rule assigns; empty = the first station of the route.",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        required=True,
        domain="[('id', 'in', allowed_user_ids)]",
    )
    allowed_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_allowed_user_ids",
    )

    @api.depends("work_center_id")
    def _compute_allowed_user_ids(self):
        """The people of the station (its members, or the holders of its acts'
        roles when it has none); officers for a rule without a station."""
        officers = self.env.ref("disbursement.group_disbursement_officer").users
        for rule in self:
            rule.allowed_user_ids = (
                rule.work_center_id.sudo()._responsible_users()[0]
                if rule.work_center_id
                else officers
            )

    @api.constrains("work_center_id", "user_id")
    def _check_user_in_station(self):
        for rule in self.filtered("work_center_id"):
            members = rule.work_center_id.sudo()._active_members()
            if members and rule.user_id not in members:
                raise ValidationError(
                    _("%(user)s is not a member of %(station)s.")
                    % {
                        "user": rule.user_id.display_name,
                        "station": rule.work_center_id.display_name,
                    }
                )

    @api.model
    def _find_for_request(self, request):
        """Return the first rule (by sequence) matching ``request``.

        Hierarchical dimensions (department / fund / activity) match on the
        whole ancestor subtree: a rule set on a parent account covers requests
        on any of its descendants. This mirrors the parent_path matching the
        budget engine uses (see budget_appropriation.py). A rule leaves a
        criterion empty to act as a wildcard for that dimension.
        """
        # Pin ("active", "=", True) explicitly rather than relying on the
        # implicit active_test: the "Apply Rules to Pending Requests" server
        # action is bound to a list whose action context sets
        # active_test=False, and that context leaks into this search.
        domain = [("active", "=", True), ("user_id.active", "=", True)]
        # The rules of the station the request is at; those without a station
        # belong to the first station of the route.
        station = request.work_center_id
        first = request._work_center_route().line_ids[:1].work_center_ids
        stations = station.ids + ([False] if not station or station in first else [])
        domain.append(("work_center_id", "in", stations))
        for field in self._CRITERIA:
            ancestors = [
                int(i)
                for i in (request[field].parent_path or "").strip("/").split("/")
                if i
            ]
            domain.append((field, "in", ancestors + [False]))
        # Every request pays a name list, so there is no single header partner
        # to key on. Match partner-type rules only when all line partners share
        # one partner type; otherwise fall back to the partner-type-agnostic
        # (wildcard) rules to avoid unpredictable routing.
        line_ptypes = request.line_ids.mapped("partner_id.partner_type_id")
        ptype = line_ptypes if len(line_ptypes) == 1 else line_ptypes.browse()
        domain.append(
            ("partner_type_id", "in", ptype.ids + [False])
        )
        for rule in self.search(domain):
            # The officer was checked when the rule was saved; the station's
            # people may have changed since.
            if not rule.work_center_id or rule.user_id in rule.allowed_user_ids:
                return rule
        return self.browse()

    @api.model
    def action_apply_to_pending(self):
        """Re-run the rules against requests at a station that have no officer.

        Exposed through a server action on the rule list so an admin can route
        a backlog after adding or editing rules. Idempotent: requests that
        already have a responsible officer are left untouched.
        """
        Request = self.env["disbursement.request"]
        pending = Request.search(
            [
                ("state", "=", "in_progress"),
                ("work_center_id", "!=", False),
                ("assigned_to", "=", False),
            ]
        )
        pending._assignment_auto_assign()
        assigned = pending.filtered("assigned_to")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Assignment Rules Applied"),
                "message": _(
                    "%(assigned)s of %(total)s pending request(s) were assigned."
                )
                % {"assigned": len(assigned), "total": len(pending)},
                "sticky": False,
            },
        }
