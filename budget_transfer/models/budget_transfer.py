import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

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

    Business rules (unchanged, ADR-0009): a transfer is a **pure move** — it
    reserves/releases nothing; a FROM line credits its bucket, a balanced TO line
    debits its bucket; sources are locked to the header (no cross-source); the
    four core dimensions are required; the two Pool Tags are optional and
    mutually exclusive. The lines are authored directly as ``budget.move.line``
    (folded, ADR-0013).

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

    READONLY_STATES = {
        "submitted": [("readonly", True)],
        "approved": [("readonly", True)],
        "posted": [("readonly", True)],
        "rejected": [("readonly", True)],
        "cancelled": [("readonly", True)],
    }

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
            ("approved", "Approved"),
            ("posted", "Posted"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        required=True,
        readonly=True,
        copy=False,
        tracking=True,
        default="draft",
    )

    transfer_type = fields.Selection(
        selection=[
            ("entry", "ทั่วไป"),
        ],
        string="Transfer Type",
        required=True,
        default="entry",
        readonly=True,
        tracking=True,
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
        required=True,
        readonly=False,
        states=READONLY_STATES,
        tracking=True,
        help="Please provide detailed justification for this budget transfer",
    )

    # User Management
    user_id = fields.Many2one(
        string="Requested by",
        comodel_name="res.users",
        copy=False,
        tracking=True,
        default=lambda self: self.env.user,
        required=True,
        readonly=False,
        states=READONLY_STATES,
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
    rejection_reason = fields.Text(
        string="Rejection Reason",
        readonly=True,
        tracking=True,
    )

    # Button Visibility
    show_submit_button = fields.Boolean(compute="_compute_button_visibility")
    show_approve_button = fields.Boolean(compute="_compute_button_visibility")
    show_reject_button = fields.Boolean(compute="_compute_button_visibility")
    show_post_button = fields.Boolean(compute="_compute_button_visibility")
    show_cancel_button = fields.Boolean(compute="_compute_button_visibility")
    show_reset_button = fields.Boolean(compute="_compute_button_visibility")

    # Validation Fields
    has_sufficient_budget = fields.Boolean(
        compute="_compute_budget_validation",
        help="Indicates if all source lines have sufficient budget",
    )
    budget_validation_message = fields.Text(
        compute="_compute_budget_validation",
        help="Detailed budget validation message",
    )

    # ------------------------------------------------------------------
    # Create — force the delegated move to be a budget entry
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # A budget transfer is always a balanced entry move; the delegated
            # move_type routes to the auto-created budget.move (_inherits).
            vals.setdefault("move_type", "entry")
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends("state", "date")
    def _compute_name(self):
        """Assign the BTR number once the transfer leaves draft."""
        for transfer in self:
            if transfer.state == "cancelled":
                continue
            has_name = transfer.name and transfer.name != "New"
            if has_name or transfer.state == "draft":
                continue
            if not has_name and transfer.date:
                new_name = self.env["ir.sequence"].next_by_code(
                    "budget.transfer"
                ) or _("New")
                transfer.name = new_name
                if new_name != _("New"):
                    transfer.move_id.ref = f"Transfer: {new_name}"

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
        for transfer in self:
            user = self.env.user
            transfer.show_submit_button = transfer.state == "draft" and (
                transfer.user_id == user or self.env.is_admin()
            )
            transfer.show_approve_button = transfer.state == "submitted"
            transfer.show_reject_button = transfer.state == "submitted"
            transfer.show_post_button = transfer.state == "approved"
            transfer.show_cancel_button = transfer.state in ("draft", "submitted")
            transfer.show_reset_button = transfer.state in (
                "submitted",
                "approved",
                "rejected",
                "cancelled",
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
        self._validate_transfer_data()
        self._validate_budget_availability()
        self.write({"state": "submitted"})
        return True

    def action_approve(self):
        is_admin = self.env.is_admin()
        if not (
            self.env.user.has_group("budget.group_budget_manager") or is_admin
        ):
            raise UserError(_("Only Budget Managers can approve transfers"))
        if not is_admin:
            for transfer in self:
                if transfer.user_id == self.env.user:
                    raise UserError(
                        _("You cannot approve your own budget transfer.")
                    )
        self._validate_budget_availability()
        self.write(
            {
                "state": "approved",
                "approver_id": self.env.user.id,
                "approval_date": fields.Datetime.now(),
            }
        )
        return True

    def action_reject(self):
        if not (
            self.env.user.has_group("budget.group_budget_manager")
            or self.env.is_admin()
        ):
            raise UserError(_("Only Budget Managers can reject transfers"))
        return self._open_rejection_wizard()

    def action_post(self):
        """Post the transfer: re-check availability, then post the balanced move.

        The move already carries the FROM/TO lines (authored through delegation);
        posting just re-stamps debit/credit/balance from each line's amount +
        direction and drives the delegated move to posted. A transfer is a pure
        budget move — no commitment is created or touched (ADR-0009).
        """
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

        for transfer in self:
            transfer.line_ids._apply_direction_amount()
            transfer.move_id.action_review()
            transfer.move_id.action_post()

        self.write({"state": "posted"})
        return True

    def action_cancel(self):
        if "posted" in self.mapped("state"):
            raise UserError(_("Cannot cancel a posted transfer"))
        for transfer in self:
            transfer.move_id.button_cancel()
        self.write({"state": "cancelled"})
        return True

    def action_reset_to_draft(self):
        if "posted" in self.mapped("state"):
            raise UserError(
                _(
                    "Cannot reset a posted transfer to draft. Its budget move is "
                    "already in effect."
                )
            )
        for transfer in self:
            if transfer.move_id.state != "draft":
                transfer.move_id.button_draft()
        self.write(
            {
                "state": "draft",
                "approver_id": False,
                "approval_date": False,
                "rejection_reason": False,
            }
        )
        return True

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
        to_lines = self.line_ids.filtered(
            lambda line: line.transfer_direction == "to"
        )
        if not from_lines:
            raise ValidationError(
                _("Please add at least one source line (Transfer FROM)")
            )
        if not to_lines:
            raise ValidationError(
                _("Please add at least one destination line (Transfer TO)")
            )

        # Every line must carry the four core dimensions (ADR-0009).
        core_dims = [
            ("department_analytic_id", "ส่วนงาน"),
            ("source_analytic_id", "แหล่งเงิน"),
            ("activity_analytic_id", "กิจกรรม"),
            ("fund_analytic_id", "กองทุน"),
        ]
        for line in self.line_ids:
            missing = [label for fname, label in core_dims if not line[fname]]
            if missing:
                raise ValidationError(
                    _(
                        "ทุกบรรทัดต้องระบุครบ 4 มิติ (ส่วนงาน / แหล่งเงิน / กิจกรรม / กองทุน).\n"
                        "บรรทัด %(account)s (%(direction)s) ยังขาด: %(missing)s"
                    )
                    % {
                        "account": line.account_id.display_name or "-",
                        "direction": "โอนออก"
                        if line.transfer_direction == "from"
                        else "โอนเข้า",
                        "missing": ", ".join(missing),
                    }
                )

        # Source (แหล่งเงิน) is locked to the header — no cross-source (ADR-0009).
        cross_source = self.line_ids.filtered(
            lambda line: line.source_analytic_id != self.source_analytic_id
        )
        if cross_source:
            raise ValidationError(
                _(
                    "All transfer lines must use the transfer's source (แหล่งเงิน). "
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

    # ------------------------------------------------------------------
    # Notifications / wizard
    # ------------------------------------------------------------------
    def _open_rejection_wizard(self):
        return {
            "name": _("Reject Budget Transfer"),
            "type": "ir.actions.act_window",
            "res_model": "budget.transfer.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_transfer_id": self.id},
        }
