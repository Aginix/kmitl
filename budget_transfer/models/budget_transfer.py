import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, formatLang

_logger = logging.getLogger(__name__)


class BudgetTransfer(models.Model):
    """Budget Transfer — a 1:1 delegated ``budget.move`` with an approval wrapper.

    ADR-0013: ``budget.transfer`` ``_inherits`` ``budget.move`` (the
    account.payment ↔ account.move pattern). The accounting header (date,
    company, currency, fiscal year, budget_type, department/source, move_type,
    and the *lines*) is the move's — accessed by the same field names through
    delegation, so no columns are duplicated. This model adds only what a
    transfer needs on top of a budget move: its own BTR number, a six-state
    approval workflow, a reason, and the requestor/approver trail.

    Business rules (ADR-0009): a FROM line credits its bucket, a balanced TO line
    debits its bucket; sources are locked to the header (no cross-source); the
    four core dimensions are required; the two Pool Tags are optional and
    mutually exclusive. The lines are authored directly as ``budget.move.line``
    (folded, ADR-0013). A transfer onto/off the coordinate of a reservation
    that owns the line's pool tag moves that reservation with it (budget
    ADR-0016, Q5/Q6).

    State lifecycle: draft → submitted → approved → posted, with rejected /
    cancelled and reset-to-draft. ``move_id.state`` follows: draft while the
    transfer is draft/submitted/approved, posted on post, cancel on cancel.
    """

    _name = "budget.transfer"
    _inherits = {"budget.move": "move_id"}
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Transfer"
    _order = "date desc, name desc, id desc"
    _rec_names_search = ["name", "ref"]

    # The delegated budget move (created up front, ADR-0013).
    move_id = fields.Many2one(
        comodel_name="budget.move",
        string="Budget Move",
        required=True,
        readonly=True,
        ondelete="cascade",
        index=True,
        auto_join=True,
    )
    # Read-only mirror of the move's BM number for the smart button. The
    # move_id delegate is required (``_inherits``); rendering it as a field on
    # the form would make the web client block a *new* record's save with a
    # "Budget Move required" error (the move only exists after save). This
    # non-required related char shows the same reference without that trap.
    move_reference = fields.Char(
        string="Budget Move",
        related="move_id.name",
        readonly=True,
    )
    # Drives the smart button's visibility (hidden on a new, unsaved record).
    # A dedicated computed flag keeps the show/hide logic independent of the
    # displayed reference value.
    has_budget_move = fields.Boolean(compute="_compute_has_budget_move")

    # Basic Information (BTR number — the move keeps its own BM number).
    name = fields.Char(
        string="Transfer Number",
        compute="_compute_name",
        readonly=False,
        store=True,
        copy=False,
        tracking=True,
        index="trigram",
        default=lambda self: _("New"),
    )

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    amount = fields.Float(
        string="Transfer Amount",
        compute="_compute_amount",
        store=True,
        digits="Budget Precision",
        readonly=True,
        tracking=True,
    )

    reason = fields.Text(
        string="Transfer Reason",
        readonly=False,
        tracking=True,
        help="Please provide detailed justification for this budget transfer",
    )

    # User Management
    user_id = fields.Many2one(
        string="Responsible",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        required=True,
        readonly=False,
    )
    approver_id = fields.Many2one(
        string="Approved by",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        readonly=True,
    )
    approval_date = fields.Datetime(
        string="Approval Date",
        copy=False,
        tracking=True,
        readonly=True,
    )
    # Button Visibility
    show_submit_button = fields.Boolean(compute="_compute_button_visibility")
    show_approve_button = fields.Boolean(compute="_compute_button_visibility")
    show_cancel_button = fields.Boolean(compute="_compute_button_visibility")
    show_reset_button = fields.Boolean(compute="_compute_button_visibility")
    # Reset from a posted transfer is shown as a separate button so it can
    # carry a confirmation warning (it unwinds a recorded budget entry).
    show_reset_posted_button = fields.Boolean(compute="_compute_button_visibility")

    # Validation Fields
    has_sufficient_budget = fields.Boolean(
        compute="_compute_budget_validation",
        help="Indicates if all source lines have sufficient budget",
    )
    budget_validation_message = fields.Text(
        compute="_compute_budget_validation",
        help="Detailed budget validation message",
    )

    # True once the BTR number has been minted — the fiscal year is then frozen
    # (it drives the number's year), even after a Reset to Draft.
    fiscal_year_locked = fields.Boolean(compute="_compute_fiscal_year_locked")

    # Single flag driving every "editable while …" readonly modifier in the
    # form (header, dimensions, reason, lines). The base opens editing in
    # ``draft`` only; a module that adds intermediate states — e.g.
    # ``budget_transfer_sarabun`` reopening a ``returned`` letter — extends
    # ``_compute_can_edit`` instead of overriding each field's modifiers.
    can_edit = fields.Boolean(compute="_compute_can_edit")

    # ------------------------------------------------------------------
    # Create — force the delegated move to be a budget entry
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # A budget transfer is always a balanced entry move; the delegated
            # move_type routes to the auto-created budget.move (_inherits).
            vals.setdefault("move_type", "entry")
            # Stamp the move as a transfer once, at creation (delegated through
            # _inherits). The link is a write-once 1:1, so this deterministic
            # flag never needs recomputing from transfer_ids.
            vals.setdefault("is_transfer", True)
        return super().create(vals_list)

    def unlink(self):
        """Also delete the delegated move.

        Odoo 16 ``unlink()`` does not cascade to ``_inherits`` parents (only
        the reverse: the move's ``ondelete="cascade"`` deletes the transfer
        when the move is deleted). Without this override, deleting a
        transfer would leave its 1:1 ``budget.move`` (and lines) orphaned in
        the ledger.
        """
        moves = self.move_id
        res = super().unlink()
        moves.unlink()
        return res

    def write(self, vals):
        """Freeze the fiscal year once the BTR number has been assigned.

        The number's year is derived from the fiscal year, so once a number is
        minted (on leaving draft) the fiscal year must stay put — even after a
        Reset to Draft, since the number is kept. Otherwise the minted number
        and the budget year would diverge.
        """
        if "account_fiscal_year_id" in vals:
            placeholders = {"New", _("New")}
            numbered = self.filtered(lambda t: t.name and t.name not in placeholders)
            if numbered:
                raise UserError(
                    _(
                        "The fiscal year is frozen once the BTR number has been "
                        "assigned — changing it would make the number inconsistent."
                    )
                )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("state", "account_fiscal_year_id")
    def _compute_name(self):
        """Assign the BTR number once the transfer leaves draft.

        The year in the BTR number comes from the fiscal year's end date
        (``account_fiscal_year_id.date_to``) — not the calendar date the
        number happens to be minted on — so it always reflects the budget
        year the transfer belongs to.
        """
        # The default name is _("New"), which is translated ("ใหม่" in Thai).
        # Recognise both the English sentinel and its translation as "unnamed",
        # otherwise the check thinks the record already has a number and never
        # pulls the sequence.
        placeholders = {"New", _("New")}
        for transfer in self:
            if transfer.state == "cancelled":
                continue
            has_name = transfer.name and transfer.name not in placeholders
            if has_name or transfer.state == "draft":
                continue
            if not has_name and transfer.account_fiscal_year_id:
                new_name = (
                    self.env["ir.sequence"]
                    .with_context(
                        ir_sequence_date=transfer.account_fiscal_year_id.date_to
                    )
                    .next_by_code("budget.transfer")
                ) or _("New")
                transfer.name = new_name
                if new_name not in placeholders:
                    transfer.move_id.ref = f"Transfer: {new_name}"

    @api.depends("name")
    def _compute_fiscal_year_locked(self):
        """Lock the fiscal year once the BTR number has been minted."""
        placeholders = {"New", _("New")}
        for transfer in self:
            transfer.fiscal_year_locked = bool(
                transfer.name and transfer.name not in placeholders
            )

    @api.depends("state")
    def _compute_can_edit(self):
        """The transfer's data is editable in ``draft`` only. Modules that add
        intermediate states extend this (super() + reopen) rather than
        re-declaring each field's readonly modifier."""
        for transfer in self:
            transfer.can_edit = transfer.state == "draft"

    @api.depends("move_id")
    def _compute_has_budget_move(self):
        """True once the delegated move exists (i.e. the record is saved)."""
        for transfer in self:
            transfer.has_budget_move = bool(transfer.move_id)

    @api.depends("line_ids.amount", "line_ids.transfer_direction")
    def _compute_amount(self):
        """Total transferred = Σ FROM-line amounts (should equal Σ TO)."""
        for transfer in self:
            transfer.amount = sum(
                transfer.line_ids.filtered(
                    lambda line: line.transfer_direction == "from"
                ).mapped("amount")
            )

    @api.depends("state", "user_id")
    def _compute_button_visibility(self):
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        for transfer in self:
            user = self.env.user
            transfer.show_submit_button = transfer.state == "draft" and (
                transfer.user_id == user or is_admin
            )
            transfer.show_approve_button = transfer.state == "submitted"
            # Cancel (draft/submitted → cancelled), account.payment pattern.
            transfer.show_cancel_button = transfer.state in ("draft", "submitted")
            # Reset to Draft (account.payment pattern): pull a pending transfer
            # back (owner/admin) or revive a cancelled one (manager/admin) —
            # neither unwinds a live budget entry, so no confirmation needed.
            transfer.show_reset_button = (
                transfer.state == "submitted" and (transfer.user_id == user or is_admin)
            ) or (transfer.state == "cancelled" and (is_manager or is_admin))
            # Resetting a *posted* transfer reverses a recorded budget entry —
            # manager/admin only, and gated behind a confirmation in the view.
            transfer.show_reset_posted_button = transfer.state == "posted" and (
                is_manager or is_admin
            )

    @api.depends(
        "line_ids.budget_sufficient",
        "line_ids.available_budget",
        "line_ids.amount",
        "line_ids.transfer_direction",
        "state",
    )
    def _compute_budget_validation(self):
        """Aggregate the per-line availability check over the FROM lines."""
        for transfer in self:
            from_lines = transfer.line_ids.filtered(
                lambda line: line.transfer_direction == "from"
            )
            if not from_lines or transfer.state in ("posted", "cancelled"):
                transfer.has_sufficient_budget = True
                transfer.budget_validation_message = ""
                continue

            insufficient = from_lines.filtered(lambda line: not line.budget_sufficient)
            transfer.has_sufficient_budget = not insufficient
            if insufficient:
                messages = [
                    _(
                        "Account %(code)s: Available %(available).2f, "
                        "Required %(required).2f"
                    )
                    % {
                        "code": line.account_id.code or line.account_id.display_name,
                        "available": line.available_budget,
                        "required": line.amount,
                    }
                    for line in insufficient
                ]
                transfer.budget_validation_message = _(
                    "Insufficient budget:\n%s"
                ) % "\n".join(messages)
            else:
                transfer.budget_validation_message = _("Budget validation passed")

    # ------------------------------------------------------------------
    # Onchange
    # ------------------------------------------------------------------
    @api.onchange("date")
    def _onchange_date(self):
        """Auto-populate the fiscal year from the transfer date."""
        if self.date:
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", self.date),
                    ("date_to", ">=", self.date),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if fiscal_year:
                self.account_fiscal_year_id = fiscal_year

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        if not (
            self.env.user.has_group("budget.group_budget_user") or self.env.is_admin()
        ):
            raise UserError(_("Only Budget Users can submit transfers"))
        self._validate_transfer_data()
        self._validate_budget_availability()
        self.write({"state": "submitted"})
        return True

    def action_approve(self):
        """Approve and immediately post — approval and posting are one step (no
        separate Post click). Records the approver, re-checks availability, then
        posts the delegated move."""
        is_admin = self.env.is_admin()
        if not (self.env.user.has_group("budget.group_budget_manager") or is_admin):
            raise UserError(_("Only Budget Managers can approve transfers"))
        if not is_admin:
            for transfer in self:
                if transfer.user_id == self.env.user:
                    raise UserError(_("You cannot approve your own budget transfer."))
        self.invalidate_recordset(
            ["has_sufficient_budget", "budget_validation_message"]
        )
        self._validate_transfer_data()
        self._validate_budget_availability()
        self.write(
            {
                "approver_id": self.env.user.id,
                "approval_date": fields.Datetime.now(),
            }
        )
        self._post_transfer()
        return True

    def action_post(self):
        """Post the transfer directly (kept for API / admin use — the normal
        flow posts automatically on approval). Re-checks availability first."""
        if not (
            self.env.user.has_group("budget.group_budget_manager")
            or self.env.is_admin()
        ):
            raise UserError(_("Only Budget Managers can post transfers"))

        self.invalidate_recordset(
            ["has_sufficient_budget", "budget_validation_message"]
        )
        self._validate_transfer_data()
        self._validate_budget_availability()
        self._post_transfer()
        return True

    def _post_transfer(self):
        """Stamp the FROM/TO lines onto the delegated move and post it.

        The move already carries the lines (authored through delegation); this
        re-stamps debit/credit/balance from each line's amount + direction, adds
        the top-up / release of the reservations it lands on, and drives the
        move to posted.
        """
        commitments = self.env["budget.commitment"]
        for transfer in self:
            transfer.line_ids._apply_direction_amount()
            commitments |= transfer._apply_pool_reservations()
            transfer.move_id.action_review()
            transfer.move_id.action_post()
        self.write({"state": "posted"})
        commitments._check_ledger_limits()
        commitments._sync_state()

    def action_cancel(self):
        if "posted" in self.mapped("state"):
            raise UserError(_("Cannot cancel a posted transfer"))
        for transfer in self:
            transfer.move_id.button_cancel()
        self.write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        """Reset to draft (account.payment pattern). Resetting a posted or
        cancelled transfer un-posts its delegated budget move — so it is
        restricted to Budget Managers / admins, unwinding the effect on
        Current Budget."""
        is_manager = self.env.user.has_group("budget.group_budget_manager")
        is_admin = self.env.is_admin()
        commitments = self.env["budget.commitment"]
        for transfer in self:
            if transfer.state in ("posted", "cancelled") and not (
                is_manager or is_admin
            ):
                raise UserError(
                    _(
                        "Only Budget Managers can reset a posted or cancelled "
                        "transfer to draft."
                    )
                )
            if transfer.state == "posted":
                commitments |= transfer._unwind_pool_reservations()
            if transfer.move_id.state != "draft":
                transfer.move_id.button_draft()
        self.write(
            {
                "state": "draft",
                "approver_id": False,
                "approval_date": False,
            }
        )
        commitments._check_ledger_limits()
        commitments._sync_state()
        return True

    # ------------------------------------------------------------------
    # Reservation top-up / release (budget ADR-0016, Q5/Q6)
    # ------------------------------------------------------------------
    def _apply_pool_reservations(self):
        """A TO line landing on the exact coordinate of an active reservation
        that owns the line's pool tag adds a ``reserve −X`` top-up to the
        transfer's own move (the reservation's cap rises by X); a FROM line out
        of such a coordinate draws the free money there first and releases the
        rest, never beyond the reservation's unobligated remainder (budget
        ADR-0016, Q5). Returns the reservations touched."""
        self.ensure_one()
        commitments = self.env["budget.commitment"]
        if self.move_id.line_ids.filtered("commitment_id"):
            return commitments  # already applied (idempotent re-post)
        free = {}  # unreserved money left per owner's coordinate
        for line in self.line_ids.filtered("transfer_direction"):
            commitment = line._pool_owner()
            if not commitment:
                continue
            amount = line.amount or 0.0
            if line.transfer_direction == "from":
                # Free money at the coordinate goes first; only the rest is
                # released from the reservation.
                if commitment not in free:
                    free[commitment] = max(line._free_budget(), 0.0)
                from_free = min(amount, free[commitment])
                free[commitment] -= from_free
                amount -= from_free
                rounding = commitment.currency_id.rounding or 0.01
                if float_compare(amount, 0.0, precision_rounding=rounding) <= 0:
                    continue
                # On a ถัวจ่าย slip only this code's share may go (ADR-0017).
                free_to_release = commitment._ledger_unobligated(line.account_id)
                if (
                    float_compare(
                        amount,
                        free_to_release,
                        precision_rounding=rounding,
                    )
                    > 0
                ):
                    raise UserError(
                        _(
                            "Cannot transfer %(amount)s out of reservation %(name)s: "
                            "only %(free)s of it is not yet obligated."
                        )
                        % {
                            "amount": formatLang(
                                self.env, amount, currency_obj=commitment.currency_id
                            ),
                            "name": commitment.display_name,
                            "free": formatLang(
                                self.env,
                                free_to_release,
                                currency_obj=commitment.currency_id,
                            ),
                        }
                    )
                amount = -amount
            commitment._post_transfer_event(line, amount)
            commitments |= commitment
        return commitments

    def _unwind_pool_reservations(self):
        """Remove the top-up / release lines before the move is un-posted;
        block when a reservation no longer has a top-up free to give back.

        A top-up/release whose event was already cancelled (its reservation was
        cancelled) has been negated by a reversal move of its own (ADR-0016,
        Q6): that reversal is cancelled together with the line, so neither is
        left behind as a phantom reservation."""
        self.ensure_one()
        commitments = self.env["budget.commitment"]
        ledger_lines = self.move_id.line_ids.filtered("commitment_id")
        for ledger_line in ledger_lines:
            commitment = ledger_line.commitment_id
            event = ledger_line.commitment_line_id
            amount = -ledger_line.balance  # + top-up, − release
            rounding = commitment.currency_id.rounding or 0.01
            if event.state == "cancel":
                reversals = (
                    self.env["budget.move.line"]
                    .sudo()
                    .search(
                        [
                            ("commitment_line_id", "=", event.id),
                            ("parent_state", "=", "posted"),
                            ("move_id", "!=", self.move_id.id),
                        ]
                    )
                    .move_id
                )
                reversals.with_context(budget_ledger_posting=True).button_cancel()
            elif (
                float_compare(
                    amount,
                    commitment._ledger_unobligated(ledger_line.account_id),
                    precision_rounding=rounding,
                )
                > 0
            ):
                raise UserError(
                    _(
                        "Cannot reset transfer %(transfer)s: reservation %(name)s "
                        "has already obligated part of the %(amount)s it received "
                        "from this transfer."
                    )
                    % {
                        "transfer": self.display_name,
                        "name": commitment.display_name,
                        "amount": formatLang(
                            self.env, amount, currency_obj=commitment.currency_id
                        ),
                    }
                )
            ledger_line.sudo().with_context(budget_ledger_posting=True).unlink()
            commitment.sudo().with_context(budget_ledger_posting=True).amount -= amount
            event.sudo().action_cancel()
            commitments |= commitment
        return commitments

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _validate_transfer_data(self):
        self.ensure_one()
        if not self.account_fiscal_year_id:
            raise ValidationError(_("Please set the fiscal year"))
        if not self.line_ids:
            raise ValidationError(_("Please add transfer lines"))

        from_lines = self.line_ids.filtered(
            lambda line: line.transfer_direction == "from"
        )
        to_lines = self.line_ids.filtered(lambda line: line.transfer_direction == "to")
        if not from_lines:
            raise ValidationError(
                _("Please add at least one source line (Transfer FROM)")
            )
        if not to_lines:
            raise ValidationError(
                _("Please add at least one destination line (Transfer TO)")
            )

        self._validate_core_dimensions()
        self._validate_line_policies()

        # Source is locked to the header — no cross-source transfers (ADR-0009).
        cross_source = self.line_ids.filtered(
            lambda line: line.source_analytic_id != self.source_analytic_id
        )
        if cross_source:
            raise ValidationError(
                _(
                    "All transfer lines must use the transfer's source. "
                    "Cross-source transfers are not allowed."
                )
            )

        from_amount = sum(from_lines.mapped("amount"))
        to_amount = sum(to_lines.mapped("amount"))
        if abs(from_amount - to_amount) > 0.01:
            raise ValidationError(
                _(
                    "Transfer must be balanced. From amount: {:,.2f}, "
                    "To amount: {:,.2f}"
                ).format(from_amount, to_amount)
            )
        if from_amount <= 0:
            raise ValidationError(_("Transfer amount must be greater than zero"))

    # Business-policy checks — unlike the structural checks above, these may be
    # switched on/off: ``budget_transfer_exception`` turns each into an
    # ``exception.rule`` and skips the hard check here.
    _TRANSFER_CORE_DIMS = (
        ("department_analytic_id", "Department"),
        ("source_analytic_id", "Source"),
        ("activity_analytic_id", "Activity"),
        ("fund_analytic_id", "Fund"),
    )

    def _get_lines_missing_core_dims(self):
        self.ensure_one()
        return self.line_ids.filtered(
            lambda line: not all(line[fname] for fname, _l in self._TRANSFER_CORE_DIMS)
        )

    def _validate_core_dimensions(self):
        """Every line must carry the four core dimensions (ADR-0009)."""
        line = self._get_lines_missing_core_dims()[:1]
        if line:
            missing = [
                label for fname, label in self._TRANSFER_CORE_DIMS if not line[fname]
            ]
            raise ValidationError(
                _(
                    "All lines must specify all 4 core dimensions (Department / Source / Activity / Fund).\n"
                    "Line %(account)s (%(direction)s) is missing: %(missing)s"
                )
                % {
                    "account": line.account_id.display_name or "-",
                    "direction": "Transfer Out"
                    if line.transfer_direction == "from"
                    else "Transfer In",
                    "missing": ", ".join(missing),
                }
            )

    def _validate_line_policies(self):
        """Pool-Tag and uniqueness policies on the lines (ADR-0009 / ADR-0012)."""
        lines = self.line_ids
        if lines._get_lines_with_both_tags():
            raise ValidationError(
                _(
                    "Each line may carry only one supplementary dimension — "
                    "KMITL Project or Procurement Plan, not both."
                )
            )
        for line in lines._get_lines_tag_account_mismatch():
            if line.kmitl_project_analytic_id and not line.account_is_project:
                raise ValidationError(
                    _(
                        "The Project/Activity dimension may only be used with "
                        "project-type budget accounts (is_project)."
                    )
                )
            raise ValidationError(
                _(
                    "The Procurement Plan dimension may only be used with "
                    "procurement-plan-type budget accounts."
                )
            )
        if lines._get_duplicate_lines():
            raise ValidationError(
                _(
                    "Duplicate transfer line found. Each combination of "
                    "direction, budget account and analytic distribution must "
                    "be unique."
                )
            )

    def _validate_budget_availability(self):
        self.ensure_one()
        if not self.has_sufficient_budget:
            raise ValidationError(
                _("Insufficient budget for transfer:\n{}").format(
                    self.budget_validation_message
                )
            )

    def action_view_budget_move(self):
        """Open the delegated budget move (the ledger entry) behind this transfer."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Budget Move"),
            "res_model": "budget.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }
