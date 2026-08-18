from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from odoo.addons.budget.models.budget_commitment import BudgetCommitment as Core


class BudgetCommitment(models.Model):
    """Cross-charge (ถัวจ่าย) reservations: one slip pooling several budget codes.

    The core journey is form-first single-code (the header IS the reserve
    line). This extension adds the minority multi-code case (ADR 0006):

    - ``is_cross_charge`` is a **UI affordance only** (ADR 0010 pattern) — the
      reserve lines stay the single source of truth, gated server-side by the
      ``cross_chargeable`` flag constraint. Switching modes clears/seeds the
      now-active side.
    - In cross-charge mode the user types reserve lines directly in the grid
      (a draft commitment is the staging area, ADR 0006); the header
      account/amount become a mirror of the lines.
    - The reservation picker returns as a browse/edit tool on cross-charge
      slips, now supporting **edit**: it reopens with the current figures
      seeded so they can be corrected instead of re-entered.
    """

    _inherit = "budget.commitment"

    is_cross_charge = fields.Boolean(
        string="ถัวจ่าย",
        default=False,
        tracking=True,
        readonly=False,
        states=Core.READONLY_STATES,
        help=(
            "ใบจองถัวจ่ายใช้รหัสงบประมาณได้หลายรหัสในใบเดียว "
            "(ทุกรหัสต้องติ๊ก ถัวจ่ายได้) โดยกรอกบรรทัดจองเองในตาราง — "
            "ใบจองปกติใช้รหัสเดียวจากหัวเอกสาร"
        ),
    )

    # Cross-charge slips derive account_id from their first reserve line —
    # relaxing required here drops the DB NOT NULL so the INSERT succeeds even
    # when the readonly header field is omitted from the save RPC.
    account_id = fields.Many2one(
        comodel_name="budget.account",
        string="รหัสงบประมาณ",
        required=False,
        index=True,
        domain="[('budgetable', '=', True), ('budget_type', '=', 'expense')]",
        tracking=True,
        states=Core.READONLY_STATES,
    )

    @api.constrains("account_id", "is_cross_charge")
    def _check_account_required_for_non_cross_charge(self):
        for record in self:
            if not record.is_cross_charge and not record.account_id:
                raise ValidationError(_("รหัสงบประมาณ is required."))

    def _check_positive_amount(self):
        """Skip the cap-must-be-positive guard for cross-charge slips.

        In cross-charge mode amount is derived from lines at create/write time;
        an empty draft (no lines yet) is a valid staging state.
        """
        for record in self:
            if record.is_cross_charge:
                continue
            if record.amount <= 0:
                raise UserError(_("Commitment cap amount must be positive."))

    # --- ORM sync: derive header from line commands (create/write) ---
    # The header account_id/amount fields are readonly in cross-charge mode, so
    # the web client never includes them in the save payload — only the line
    # grid is editable. We fill them from the line commands before super() runs
    # so every DB constraint and Python @api.constrains sees the correct values.

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("is_cross_charge"):
                self._fill_cross_charge_header(vals)
        return super().create(vals_list)

    def write(self, vals):
        result = super().write(vals)
        if "line_ids" in vals:
            for record in self.filtered("is_cross_charge"):
                record._sync_cross_charge_header_stored()
        return result

    def _fill_cross_charge_header(self, vals):
        """Populate account_id and amount from line commands (create path)."""
        first_account = False
        total = 0.0
        for cmd in vals.get("line_ids", []):
            if cmd[0] not in (0, 1):
                continue
            lv = cmd[2]
            if lv.get("move_type", "reserve") != "reserve":
                continue
            if lv.get("state", "posted") != "posted":
                continue
            if not first_account and lv.get("account_id"):
                first_account = lv["account_id"]
            total += lv.get("amount", 0.0)
        if first_account and not vals.get("account_id"):
            vals["account_id"] = first_account
        if total and not vals.get("amount"):
            vals["amount"] = total

    def _sync_cross_charge_header_stored(self):
        """Re-sync header account_id and amount from saved reserve lines."""
        for record in self:
            reserve = record.line_ids.filtered(
                lambda l: l.move_type == "reserve" and l.state == "posted"
            )
            if not reserve:
                continue
            new_account = reserve[0].account_id
            new_amount = sum(reserve.mapped("amount"))
            to_write = {}
            if record.account_id != new_account:
                to_write["account_id"] = new_account.id
            if record.amount != new_amount:
                to_write["amount"] = new_amount
            if to_write:
                record.write(to_write)

    @api.onchange("is_cross_charge")
    def _onchange_is_cross_charge(self):
        """Switching modes clears/seeds the now-inactive/active side, so the
        form can never say one thing while the reserve action does another."""
        if self.is_cross_charge:
            # Upgrade to ถัวจ่าย: carry the single-code data already typed into
            # the grid as its first line, instead of asking for it again.
            if not self.line_ids and self.account_id:
                self.line_ids = [
                    Command.create(
                        {
                            "move_type": "reserve",
                            "account_id": self.account_id.id,
                            "amount": self.amount,
                            "analytic_distribution": self.analytic_distribution,
                            "name": _("Reservation"),
                        }
                    )
                ]
        else:
            # Back to single-code: the staged lines are the inactive side now;
            # the header (kept in sync below) already carries the first line.
            self.line_ids = [Command.clear()]

    @api.onchange("line_ids")
    def _onchange_line_ids_sync_header(self):
        """Header mirrors the grid (ADR 0006: lines are the truth): account =
        first reserve line's code, amount = total staged — the money is typed
        once, in the grid, never a second time on the header."""
        if not self.is_cross_charge:
            return
        reserve = self.line_ids.filtered(
            lambda l: l.move_type == "reserve" and l.state == "posted"
        )
        if reserve:
            self.account_id = reserve[0].account_id
            self.amount = sum(reserve.mapped("amount"))

    def _create_reserve_line_from_header(self):
        """A cross-charge slip's lines are typed by the user — never synthesized
        from the header (which code would it pick?)."""
        self.ensure_one()
        if self.is_cross_charge:
            raise UserError(
                _(
                    "ใบจองถัวจ่ายต้องมีบรรทัดจองอย่างน้อย 1 บรรทัด — "
                    "กรอกรหัสงบประมาณและจำนวนเงินในตาราง Ledger Lines"
                )
            )
        return super()._create_reserve_line_from_header()

    # --- Reservation picker (browse/edit tool for cross-charge slips) ---

    def _check_reservation_editable(self):
        """The picker may (re)write reserve lines while the slip is draft
        (staging, ADR 0006) or reserved with nothing obligated yet. Once a
        downstream document has obligated against it, the figures are frozen —
        return (คืนจอง) or cancel instead of editing."""
        self.ensure_one()
        if self.state == "draft":
            return
        if self.state == "reserved" and not self.total_obligated:
            return
        raise UserError(
            _(
                "Budget can only be (re)selected while the reservation is "
                "draft, or reserved with nothing obligated yet."
            )
        )

    def action_open_reservation_picker(self):
        """Open the budget reservation picker (hierarchy + per-row available).

        Scoped to this commitment's dimension combination. When reserve lines
        already exist they are passed as ``edit_selections`` so the picker
        opens in edit mode: filter bar seeded with the slip's own dimensions
        and the current amounts filled in, ready to correct.
        """
        self.ensure_one()
        self._check_reservation_editable()
        account = self.account_id
        root = account
        while root and root.parent_id:
            root = root.parent_id
        context = {
            "res_model": "budget.commitment",
            "res_id": self.id,
            "select_only": False,
            "default_fiscal_year_id": self.account_fiscal_year_id.id,
            "default_root_account_id": root.id if root else False,
            "default_department_analytic_id": self.department_analytic_id.id or False,
            "default_source_analytic_id": self.source_analytic_id.id or False,
            "default_fund_analytic_id": self.fund_analytic_id.id or False,
            "default_activity_analytic_id": self.activity_analytic_id.id or False,
        }
        posted_reserve = self.line_ids.filtered(
            lambda l: l.state == "posted" and l.move_type == "reserve"
        )
        if posted_reserve:
            per_account = {}
            for line in posted_reserve:
                per_account[line.account_id.id] = (
                    per_account.get(line.account_id.id, 0.0) + line.amount
                )
            context["edit_selections"] = [
                {"account_id": account_id, "amount": amount}
                for account_id, amount in per_account.items()
            ]
        return {
            "type": "ir.actions.client",
            "tag": "budget_reservation_picker",
            "target": "new",
            "name": _("เลือกงบประมาณ"),
            "context": context,
        }

    def apply_reservation_selection(self, selections, dims=None):
        """Write reserve lines from the picker.

        ``selections`` = ``[{"account_id": int, "amount": float}, ...]``.
        Replaces the commitment's current reserve lines (re-selection cancels
        the old ones), stamps the chosen dimensions (``dims`` =
        ``analytic_distribution``) on the header and each line, and lifts the
        cap to cover the total. Cross-charge (>1 code) is gated by the
        ``cross_chargeable`` constraint. Allowed while draft or reserved with
        nothing obligated; on an active slip availability is re-checked after
        the replacement (see :meth:`_check_replacement_availability`).
        """
        self.ensure_one()
        self._check_reservation_editable()
        was_active = self.state != "draft"
        selections = [
            s for s in (selections or []) if s.get("account_id") and s.get("amount")
        ]
        if not selections:
            raise UserError(_("Select at least one budget code with an amount."))

        # Re-selection: cancel the existing posted reserve lines first.
        self.line_ids.filtered(
            lambda l: l.state == "posted" and l.move_type == "reserve"
        ).action_cancel()

        distribution = dims if dims is not None else self.analytic_distribution
        total = sum(s["amount"] for s in selections)
        line_cmds = [
            (
                0,
                0,
                {
                    "move_type": "reserve",
                    "account_id": s["account_id"],
                    "amount": s["amount"],
                    "analytic_distribution": distribution,
                    "name": _("Reservation"),
                },
            )
            for s in selections
        ]
        vals = {"line_ids": line_cmds, "account_id": selections[0]["account_id"]}
        if dims is not None:
            vals["analytic_distribution"] = dims or False
        if not self.amount or self.amount < total:
            vals["amount"] = total
        self.write(vals)
        if was_active:
            self._check_replacement_availability()
        return True

    def _check_replacement_availability(self):
        """Availability re-check after editing an ACTIVE (reserved) slip.

        While draft, :meth:`_check_reserve_availability` compares
        ``available >= amount`` because a draft's own lines are not yet counted
        as used (the controller counts active commitments only). An active
        slip's replacement lines ARE already posted and subtracted from the
        control-node available — so the pool is over-committed exactly when
        available drops below zero. Skipped when ``budget.allow_negative``.
        """
        self.ensure_one()
        allow_negative = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        )
        if allow_negative:
            return
        controller = self.env["budget.controller"]
        rounding = self.currency_id.rounding or 0.01
        avail_distribution = self._availability_distribution()
        reserve_lines = self.line_ids.filtered(
            lambda l: l.state == "posted" and l.move_type == "reserve"
        )
        for account in reserve_lines.mapped("account_id"):
            available = controller.get_available(
                account,
                avail_distribution,
                self.account_fiscal_year_id.id,
                self.company_id.id,
            )
            if float_compare(available, 0.0, precision_rounding=rounding) < 0:
                raise UserError(
                    _(
                        "Insufficient budget: editing this reservation would "
                        "overdraw %(code)s by %(shortfall).2f at the control "
                        "node."
                    )
                    % {
                        "code": account.display_name,
                        "shortfall": -available,
                    }
                )
