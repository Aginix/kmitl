# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models

OFFICER_GROUP = "finance_kmitl.group_finance_kmitl_user_out"


class FinanceAssignmentRule(models.Model):
    """Routing rule that maps a payment voucher to a finance officer.

    An outbound voucher is matched against these rules (ordered by ``sequence``)
    the moment it is created, and the first matching rule's officer is stored in
    ``account.payment.assigned_to``. Matching is advisory: it only pre-fills who
    carries the voucher from draft to paid and raises a To-Do; it never locks who
    is allowed to confirm it.
    """

    _name = "finance.assignment.rule"
    _description = "Finance Assignment Rule"
    _order = "sequence, id"
    _rec_name = "user_id"

    # Hierarchical dimension criteria, matched over the whole ancestor subtree.
    # An empty criterion behaves as a wildcard (matches any value there).
    # The flat criteria — partner type and paying account — are matched on
    # equality in ``_find_for_payment`` instead, because neither has a tree.
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
    paying_account_id = fields.Many2one(
        "account.payment.method.line",
        string="Paying Account",
        ondelete="restrict",
        # Every outbound account, not only the ใบสำคัญจ่าย (PV) ones the
        # disbursement flow uses: routing covers every outbound voucher this
        # office raises, so a rule has to be able to name the account a loan
        # voucher (PVR/PAR) is paid from too.
        domain=[("payment_type", "=", "outbound")],
        help="หัวจ่าย — the account the money leaves from, which names the "
        "payment method too, so a rule on a cheque account routes every cheque "
        "paid from it. Leave empty to match any paying account.",
    )

    user_id = fields.Many2one(
        "res.users",
        string="Assigned Officer",
        required=True,
        domain=lambda self: [
            ("groups_id", "in", self.env.ref(OFFICER_GROUP).ids)
        ],
    )

    @api.model
    def _find_for_payment(self, payment):
        """Return the first rule (by sequence) matching ``payment``.

        Hierarchical dimensions (department / fund / activity) match on the
        whole ancestor subtree: a rule set on a parent account covers vouchers
        on any of its descendants. This mirrors the parent_path matching the
        budget engine uses (see budget_appropriation.py). A rule leaves a
        criterion empty to act as a wildcard for that dimension.

        Partner type and paying account are flat: neither is a tree, so both
        match on equality.

        The dimensions are read off the payment directly: they live on the
        journal entry (``accounting_kmitl`` puts ``analytic.distribution.mixin``
        on ``account.move``) and the payment delegates to it through
        ``_inherits``.
        """
        # Pin ("active", "=", True) explicitly rather than relying on the
        # implicit active_test: the "Apply Rules to Pending Payments" server
        # action is bound to a list whose action context sets
        # active_test=False, and that context leaks into this search.
        domain = [("active", "=", True), ("user_id.active", "=", True)]
        for field in self._CRITERIA:
            ancestors = [
                int(i)
                for i in (payment[field].parent_path or "").strip("/").split("/")
                if i
            ]
            domain.append((field, "in", ancestors + [False]))
        # A voucher pays exactly one payee, so its partner type is unambiguous —
        # unlike a disbursement request, which pays a name list.
        domain.append(
            (
                "partner_type_id",
                "in",
                payment.partner_id.partner_type_id.ids + [False],
            )
        )
        # And it leaves from exactly one หัวจ่าย, which is the only place a
        # paying account can be recorded — so this too is unambiguous. It is set
        # before the voucher is saved on both roads in: the disbursement puts it
        # in the create values, and a voucher filled in by hand cannot be
        # confirmed for the bank without one.
        domain.append(
            ("paying_account_id", "in", payment.payment_method_line_id.ids + [False])
        )
        return self.search(domain, limit=1)

    @api.model
    def action_apply_to_pending(self):
        """Re-run the rules against still-unassigned vouchers in the office's hands.

        Exposed through a server action on the rule list so an admin can route a
        backlog after adding or editing rules. Idempotent: vouchers that already
        have a responsible officer are left untouched, and a voucher the finance
        office has finished with (paid) or cancelled is no longer anybody's work
        to take.
        """
        Payment = self.env["account.payment"]
        pending = Payment.search(
            [
                ("payment_type", "=", "outbound"),
                ("finance_state", "in", ("draft", "confirmed")),
                ("assigned_to", "=", False),
                ("state", "!=", "cancel"),
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
                    "%(assigned)s of %(total)s pending voucher(s) were assigned."
                )
                % {"assigned": len(assigned), "total": len(pending)},
                "sticky": False,
            },
        }
