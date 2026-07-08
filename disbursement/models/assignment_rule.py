# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class DisbursementAssignmentRule(models.Model):
    """Routing rule that maps a disbursement request to a verification officer.

    When a request reaches the ``signed`` state it is matched against these
    rules (ordered by ``sequence``) and the first matching rule's officer is
    stored in ``disbursement.request.assigned_to``. Matching is advisory: it
    only pre-fills the responsible officer and raises a To-Do; it never locks
    who is allowed to validate the request.
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

    user_id = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        required=True,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                self.env.ref("disbursement.group_disbursement_officer").ids,
            )
        ],
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
        return self.search(domain, limit=1)

    @api.model
    def action_apply_to_pending(self):
        """Re-run the rules against already-signed, still-unassigned requests.

        Exposed through a server action on the rule list so an admin can route
        a backlog after adding or editing rules. Idempotent: requests that
        already have a responsible officer are left untouched.
        """
        Request = self.env["disbursement.request"]
        pending = Request.search(
            [("state", "=", "signed"), ("assigned_to", "=", False)]
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
