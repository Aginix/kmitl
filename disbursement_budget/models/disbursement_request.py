# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.disbursement.models.disbursement_request import (
    DisbursementRequest as DisbursementRequestBase,
)


class DisbursementRequest(models.Model):
    """Budget control on the disbursement request (ADR-0003).

    The request reserves nothing itself: an upstream document (PR/PO/PA/AR)
    links a reserved ``budget.commitment``, and the Rector-delegated approval —
    the final step of the two-approver flow — consumes it. Cancelling reverses
    this request's own events, or the whole commitment when it is not shared.
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
        states=DisbursementRequestBase.READONLY_STATES,
    )

    budget_account_id = fields.Many2one(
        "budget.account",
        string="Budget Account",
        domain=[("budgetable", "=", True), ("budget_type", "=", "expense")],
        tracking=True,
        copy=False,
        index=True,
        ondelete="restrict",
        states=DisbursementRequestBase.READONLY_STATES,
    )

    # True when the budget code drives the line account itself (see
    # ``_budget_account_line_account``): the account column is then hidden and
    # stamped automatically. False for ordinary disbursements, where the user
    # picks an account per line. Bridges that own such budget codes contribute to
    # this single flag so the line list has one condition to key on.
    is_budget_account_product_expense = fields.Boolean(
        string="Account Derived From Budget Account",
        compute="_compute_is_budget_account_product_expense",
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
    # Some budget codes carry their own GL account (through the product bound by
    # budget_product), so the user must not pick it by hand. A bridge that owns
    # such codes raises ``is_budget_account_product_expense`` and returns the
    # account from ``_budget_account_line_account``; the stamping itself lives
    # here and runs at ORM level, so it also lands on requests created
    # programmatically and on fields the interactive onchange cannot reach (the
    # account column is hidden).
    # A bridge overriding the compute declares the dependency it actually reads
    # (its own budget-code flag); Odoo merges ``@api.depends`` across every class
    # in the MRO that defines the method, so the base dependency below always
    # holds on top of it.
    @api.depends("budget_account_id")
    def _compute_is_budget_account_product_expense(self):
        for rec in self:
            rec.is_budget_account_product_expense = False

    def _budget_account_line_account(self):
        """Account every line must carry, or an empty recordset when the user
        picks the account by hand. Overridden per budget-code type."""
        self.ensure_one()
        return self.env["account.account"]

    def _budget_account_default_account(self):
        """GL account sharing the budget code: the account a new line starts
        with. The user may still pick another one."""
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
            if not rec.is_budget_account_product_expense:
                continue
            # The account follows the budget code unconditionally, blank
            # included: the account column is hidden for these codes — so
            # keeping the previous code's account would silently book the
            # expense against the wrong account with no way for the user to
            # correct it. A blank account is refused on submit.
            account = rec._budget_account_line_account()
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
        # Idempotent: a request returned to verification (approved -> signed)
        # keeps its consumption, so re-approving must not double-cut the budget.
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
                _("Budget commitment is required before approval. "
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
        return-to-verification round trip)."""
        self.ensure_one()
        commitment = self.budget_commitment_id
        return bool(commitment) and commitment._has_budget_event(self, "consume")

    # -------------------------------------------------------------------------
    # Workflow hooks
    # -------------------------------------------------------------------------
    def _on_final_approval(self):
        super()._on_final_approval()
        self._action_approve_budget()

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
