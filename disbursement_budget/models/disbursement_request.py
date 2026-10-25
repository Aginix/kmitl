# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, _lt, api, fields, models
from odoo.exceptions import UserError


class DisbursementRequest(models.Model):
    """Budget control on the disbursement request (ADR-0003).

    The request reserves nothing itself: an upstream document (PR/PO/PA/AR)
    links a reserved ``budget.commitment``, and the consume act — done by the
    Rector-delegated approver at the station that requires it — consumes it.
    Cancelling reverses this request's own events, or the whole commitment when
    it is not shared.
    """

    _name = "disbursement.request"
    _inherit = ["disbursement.request", "budget.commitment.mixin"]

    _commitment_id_field = "budget_commitment_id"
    _commitment_account_id_field = "budget_account_id"

    # Budget fields
    budget_commitment_id = fields.Many2one(
        "budget.commitment",
        string="Budget Commitment",
        # The fiscal year leads: only commitments of the request's year.
        domain="[('state', 'not in', ['draft', 'done', 'cancel']),"
        " ('account_fiscal_year_id', '=', account_fiscal_year_id)]",
        tracking=True,
        copy=False,
        index=True,
        ondelete="restrict",
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        tracking=True,
        copy=False,
        index=True,
        ondelete="restrict",
    )

    # Off for the money that is not the university's budget (เงินรับฝากบุคคลที่สาม,
    # เงินประกัน): the consume act is then not applicable and consumes nothing.
    consumes_budget = fields.Boolean(
        string="Consumes Budget",
        default=True,
        tracking=True,
        copy=True,
        help="Untick for money that does not draw on the budget, such as third "
        "party deposits (เงินรับฝากบุคคลที่สาม) or guarantees (เงินประกัน): "
        "the consume budget act is then not applicable.",
    )

    # True when the line account is locked to the budget code's own account
    # (see ``_budget_account_default_account``): the account column is then
    # hidden and stamped automatically. False for ordinary disbursements, where
    # lines start on that account and the user may pick another. Bridges that
    # own such budget codes contribute to this single flag so the line list has
    # one condition to key on.
    is_line_account_locked = fields.Boolean(
        string="Line Account Locked to Budget Code",
        compute="_compute_is_line_account_locked",
    )

    budget_consumed_amount = fields.Monetary(
        string="Budget Consumed",
        currency_field="currency_id",
        copy=False,
        readonly=True,
        tracking=True,
    )

    budget_consumed_date = fields.Datetime(
        string="Budget Consumed At",
        copy=False,
        readonly=True,
    )

    # Leftover reserved budget still on the linked commitment (reserved −
    # obligated). Drives the "ส่งคืนเงินเหลือจ่าย" button visibility.
    budget_available_to_obligate = fields.Monetary(
        related="budget_commitment_id.available_to_obligate",
        string="งบจองคงเหลือ",
        currency_field="currency_id",
    )

    # -------------------------------------------------------------------------
    # The consume-budget act
    # -------------------------------------------------------------------------
    @api.model
    def _disbursement_acts(self):
        return super()._disbursement_acts() + [
            {
                "code": "disbursement.consume_budget",
                "name": _lt("Consume Budget"),
                "kind": "act",
                "group": "disbursement.group_disbursement_rector_delegate",
                "sequence": 40,
                "module": "disbursement_budget",
            }
        ]

    def _disbursement_act_applicable(self, code):
        if code == "disbursement.consume_budget" and not self.consumes_budget:
            return False
        return super()._disbursement_act_applicable(code)

    can_consume_budget = fields.Boolean(compute="_compute_can_consume_budget")

    @api.depends("state", "consumes_budget", "budget_consumed_amount")
    @api.depends_context("uid")
    def _compute_can_consume_budget(self):
        for rec in self:
            rec.can_consume_budget = bool(
                rec.consumes_budget
                and not rec.budget_consumed_amount
                and rec._disbursement_act_offered("disbursement.consume_budget")
            )

    def action_consume_budget(self):
        """The act: consume the linked commitment. Idempotent, so pressing it
        again after a divert back never double-cuts the budget."""
        for rec in self:
            rec._disbursement_check_act("disbursement.consume_budget")
            if rec.consumes_budget:
                rec._action_approve_budget()
            rec._disbursement_act_done("disbursement.consume_budget")
        return True

    @api.depends("budget_commitment_id")
    def _compute_can_edit(self):
        super()._compute_can_edit()

    def _can_edit_blocked(self, kind):
        """The linked commitment carries the dimensions. (It also carries the
        budget code, which the form locks on the field itself: the budget part
        must stay open, or picking a commitment would lock the commitment
        field and the value would never be saved.)"""
        return super()._can_edit_blocked(kind) or (
            kind == "dimensions" and bool(self.budget_commitment_id)
        )

    # -------------------------------------------------------------------------
    # Budget commitment methods
    # -------------------------------------------------------------------------
    @api.onchange("budget_commitment_id")
    def _onchange_budget_commitment_id(self):
        for rec in self:
            if rec.budget_commitment_id:
                budget = rec.budget_commitment_id
                rec.budget_account_id = budget.account_id
                rec.analytic_distribution = budget.analytic_distribution

    def _log_budget_commitment_linked(self):
        self.ensure_one()
        link = f"/web#id={self.id}&model={self._name}&view_type=form"
        self.budget_commitment_id.message_post(
            body=_(
                'The disbursement request <a href="%(link)s" target="_blank">\'%(name)s\'</a> has been linked to this record.'
            )
            % {"name": self.display_name, "link": link},
            subtype_xmlid="mail.mt_comment",
        )

    def _log_budget_commitment_unlinked(self):
        self.ensure_one()
        link = f"/web#id={self.id}&model={self._name}&view_type=form"
        self.budget_commitment_id.message_post(
            body=_("The disbursement request '%(name)s' has been unlinked.")
            % {"name": self.display_name},
            subtype_xmlid="mail.mt_comment",
        )

    @api.onchange("account_fiscal_year_id")
    def _onchange_fiscal_year_clear_commitment(self):
        """The fiscal year leads: a new year drops the commitment, which must
        be picked again among that year's (see the field domain)."""
        self.budget_commitment_id = False

    @api.model_create_multi
    def create(self, vals_list):
        # A request raised with a commitment books to its year, not the year of
        # its date (e.g. an FY69 reservation disbursed in October = FY70).
        for vals in vals_list:
            if vals.get("budget_commitment_id") and not vals.get(
                "account_fiscal_year_id"
            ):
                commitment = self.env["budget.commitment"].browse(
                    vals["budget_commitment_id"]
                )
                vals["account_fiscal_year_id"] = commitment.account_fiscal_year_id.id
        records = super().create(vals_list)
        for rec in records:
            if rec.budget_commitment_id:
                rec._log_budget_commitment_linked()
        records._fill_budget_account_account_on_lines()
        return records

    def write(self, values):
        # Log unlinking if budget_commitment_id is being changed
        if "budget_commitment_id" in values:
            for rec in self:
                # Only log if there's currently a budget commitment and it's being changed
                if (
                    rec.budget_commitment_id
                    and values.get("budget_commitment_id") != rec.budget_commitment_id.id
                ):
                    rec._log_budget_commitment_unlinked()

        res = super().write(values)

        # Log linking if budget_commitment_id is set to a value
        if "budget_commitment_id" in values and values.get("budget_commitment_id"):
            for rec in self:
                rec._log_budget_commitment_linked()

        if "budget_account_id" in values or "line_ids" in values:
            self._fill_budget_account_account_on_lines()

        return res

    # -------------------------------------------------------------------------
    # Budget-account driven line account
    # -------------------------------------------------------------------------
    # A line's GL account is the one sharing the request's budget code: lines
    # start on it and the user may pick another. For some budget codes the user
    # must not pick it by hand: a bridge that owns such codes raises
    # ``is_line_account_locked`` and the account is then stamped on every line
    # at ORM level, so it also lands on requests created programmatically and on
    # fields the interactive onchange cannot reach (the account column is
    # hidden).
    # A bridge overriding the compute declares the dependency it actually reads
    # (its own budget-code flag); Odoo merges ``@api.depends`` across every class
    # in the MRO that defines the method, so the base dependency below always
    # holds on top of it.
    @api.depends("budget_account_id")
    def _compute_is_line_account_locked(self):
        for rec in self:
            rec.is_line_account_locked = False

    def _budget_account_default_account(self):
        """GL account sharing the budget code: the account every line starts
        with."""
        self.ensure_one()
        if not self.budget_account_id.code:
            return self.env["account.account"]
        return self.env["account.account"].search(
            [
                ("code", "=", self.budget_account_id.code),
                ("company_id", "=", (self.company_id or self.env.company).id),
                ("deprecated", "=", False),
            ],
            limit=1,
        )

    def _fill_budget_account_account_on_lines(self):
        for rec in self:
            if not rec.is_line_account_locked:
                continue
            # The account follows the budget code unconditionally, blank
            # included: the account column is hidden for these codes — so
            # keeping the previous code's account would silently book the
            # expense against the wrong account with no way for the user to
            # correct it. A blank account is refused on submit.
            account = rec._budget_account_default_account()
            for line in rec.line_ids.filtered(lambda l: l.account_id != account):
                line.account_id = account
                if not line.name:
                    line.name = account.name

    @api.onchange("budget_account_id", "line_ids")
    def _onchange_fill_budget_account_account(self):
        self._fill_budget_account_account_on_lines()

    def _action_approve_budget(self):
        """Consume from the pre-linked budget commitment.

        The BC is expected to be set from an upstream process (PR/PO/PA);
        this method does NOT create a new BC. It posts a single consume event
        for the DR amount, leaving the BC open for other DRs. With nothing
        obligated, the ledger liquidates the reservation directly
        (``reserve +X / consume −X``, budget ADR-0017) — an obligate step
        would be cancelled out by the consume in the same instant anyway.
        """
        self.ensure_one()
        # Idempotent: a request diverted back to an earlier station keeps its
        # consumption, so consuming again must not double-cut the budget.
        if self._has_own_budget_obligation():
            return
        commitment = self._check_commitment_obligable()
        commitment._post_budget_event(
            "consume",
            self.amount_total,
            source=self,
            name=_("Consumption: %s") % self.name,
        )
        self.budget_consumed_amount = self.amount_total
        self.budget_consumed_date = fields.Datetime.now()
        self.message_post(
            body=_("Budget consumed: %(amount)s on commitment %(name)s")
            % {"amount": self.amount_total, "name": commitment.name},
            subtype_xmlid="mail.mt_note",
        )

    def action_return_leftover_budget(self):
        """Shortcut from the DR to the leftover-return (คืนจอง) confirmation.

        Opens the same ``budget.commitment.return.wizard`` the commitment uses,
        scoped to this DR's linked commitment, and stamps this DR as the source
        document on the posted return line. The wizard works on the whole
        commitment (which may be shared across งวด), returning its full
        unconsumed remainder — consistent with the manual, no-guard policy.
        """
        self.ensure_one()
        commitment = self.budget_commitment_id
        if not commitment:
            raise UserError(_("No budget commitment linked to this request."))
        return commitment._action_return_leftover_wizard(
            res_model="disbursement.request", res_id=self.id
        )

    def _check_commitment_obligable(self):
        """Validate the linked commitment can absorb this DR's amount."""
        self.ensure_one()
        if not self.budget_commitment_id:
            raise UserError(
                _("Budget commitment is required before consuming budget. "
                  "Please link one from the upstream document.")
            )
        commitment = self.budget_commitment_id
        if commitment.state not in ("reserved", "partial"):
            raise UserError(
                _("Cannot obligate: commitment %(name)s is in state '%(state)s' "
                  "(must be 'reserved' or 'partial').")
                % {"name": commitment.name, "state": commitment.state}
            )
        if commitment.available_to_obligate < self.amount_total:
            raise UserError(
                _("Insufficient available to obligate on commitment %(name)s. "
                  "Available: %(available)s, Required: %(required)s")
                % {
                    "name": commitment.name,
                    "available": commitment.available_to_obligate,
                    "required": self.amount_total,
                }
            )
        return commitment

    def _reverse_own_commitment_lines(self, commitment):
        """Cancel only the events THIS request posted on a shared commitment
        (obligate too, for requests approved before ADR-0017), leaving the
        reservation open for other requests."""
        self.ensure_one()
        return commitment._cancel_budget_events(
            source=self, move_types=("obligate", "consume")
        )

    def _has_own_budget_obligation(self):
        """Whether this request already has a posted consume event on its
        commitment (used to keep _action_approve_budget idempotent across a
        divert back)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        return bool(commitment) and commitment._has_budget_event(self, "consume")

    # -------------------------------------------------------------------------
    # Workflow hooks
    # -------------------------------------------------------------------------
    def _on_cancel(self):
        super()._on_cancel()
        for rec in self:
            commitment = rec.budget_commitment_id
            if commitment:
                try:
                    plan_owned = (
                        "procurement_plan_id" in commitment._fields
                        and commitment.procurement_plan_id
                    )
                    is_shared = (
                        plan_owned
                        or len(commitment.disbursement_request_ids) > 1
                    )
                    if is_shared:
                        rec._reverse_own_commitment_lines(commitment)
                        rec.message_post(
                            body=_(
                                "Reversed this request's lines on shared "
                                "commitment %s."
                            )
                            % commitment.name,
                            subtype_xmlid="mail.mt_note",
                        )
                    else:
                        rec._cancel_budget_commitment()
                        rec.message_post(
                            body=_("Budget commitment %s cancelled.")
                            % commitment.name,
                            subtype_xmlid="mail.mt_note",
                        )
                except UserError as e:
                    rec.message_post(
                        body=_("Warning: %s") % str(e),
                        subtype_xmlid="mail.mt_note",
                    )
            # A cancelled request no longer has budget obligated/consumed on
            # its behalf (the lines above already reversed or cancelled the
            # commitment side); clearing these keeps every reader that
            # branches on "did this request commit budget" correct without
            # having to also check state, and hides the leftover-return
            # button, which depends on budget_consumed_amount.
            rec.budget_consumed_amount = 0.0
            rec.budget_consumed_date = False
