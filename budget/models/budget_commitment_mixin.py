import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class BudgetCommitmentMixin(models.AbstractModel):
    """Budget Commitment Mixin - API Interface for Budget Commitment Integration.

    Provides a standardized interface for other modules to create and manage
    budget commitments. Supports both the new multi-line ledger API and
    backward-compatible single-line API.

    Usage:
        class PurchaseOrder(models.Model):
            _inherit = ['purchase.order', 'budget.commitment.mixin']

            _commitment_id_field = 'budget_commitment_id'
            _commitment_account_id_field = 'budget_account_id'

            def action_reserve_budget(self):
                commitment = self._create_budget_commitment(
                    amount=self.amount_total,
                    activity_analytic_id=self.activity_id,
                    fund_analytic_id=self.fund_id,
                )
                return commitment
    """

    _name = "budget.commitment.mixin"
    _description = "Budget Commitment Mixin"

    _commitment_id_field = "budget_commitment_id"
    _commitment_account_id_field = "budget_account_id"

    def _get_commitment_title(self):
        """The ชื่อรายการจอง to stamp on a commitment this host reserves.

        ``budget.commitment.title`` is required — a reservation is picked by what
        it is for, not by its number — so every host must name the one it
        creates. Falls back through the host's own human label (``title`` on
        purchase.request, ``description`` on approval.request) to its
        ``display_name``, which is never empty.
        """
        self.ensure_one()
        for fname in ("title", "description"):
            if fname in self._fields:
                # First non-blank line: description is a Text on both hosts, and a
                # whitespace-only value must not win (nor blow up on splitlines).
                for line in (self[fname] or "").splitlines():
                    if line.strip():
                        return line.strip()
        return self.display_name

    def _get_commitment_field_value(self, field_name):
        """Get the value of a dynamic commitment field."""
        self.ensure_one()
        if field_name == "commitment_id":
            actual = getattr(
                self.__class__, "_commitment_id_field", "budget_commitment_id"
            )
        elif field_name == "account_id":
            actual = getattr(
                self.__class__, "_commitment_account_id_field", "budget_account_id"
            )
        else:
            raise ValueError("Unknown field_name: %s" % field_name)

        if hasattr(self, actual):
            return getattr(self, actual)
        return False

    def _set_commitment_field_value(self, field_name, value):
        """Set the value of a dynamic commitment field."""
        self.ensure_one()
        if field_name == "commitment_id":
            actual = getattr(
                self.__class__, "_commitment_id_field", "budget_commitment_id"
            )
        else:
            raise ValueError("Unknown field_name: %s" % field_name)

        if hasattr(self, actual):
            setattr(self, actual, value)
        else:
            _logger.warning("Field %s not found on model %s", actual, self._name)

    def _create_budget_commitment(
        self,
        amount,
        activity_analytic_id,
        fund_analytic_id,
        department_analytic_id=None,
        source_analytic_id=None,
        ref=None,
        description=None,
        auto_reserve=True,
        **kwargs,
    ):
        """Create a budget commitment with a reserve line.

        Backward-compatible API: creates a commitment with one reserve line
        from the individual analytic parameters.
        """
        self.ensure_one()

        budget_account_id = self._get_commitment_field_value("account_id")
        if not budget_account_id:
            raise ValidationError(
                _("Budget account field '%s' is not set on this record")
                % getattr(
                    self.__class__,
                    "_commitment_account_id_field",
                    "budget_account_id",
                )
            )

        # Check for existing cancelled commitment to reuse
        existing = self._get_commitment_field_value("commitment_id")
        if existing and existing.state in ["cancel", "draft"]:
            commitment = self._reuse_cancelled_commitment(
                existing,
                amount,
                activity_analytic_id,
                fund_analytic_id,
                department_analytic_id,
                source_analytic_id,
                ref,
                description,
                budget_account_id,
                **kwargs,
            )
        else:
            commitment = self._create_new_commitment(
                amount,
                activity_analytic_id,
                fund_analytic_id,
                department_analytic_id,
                source_analytic_id,
                ref,
                description,
                budget_account_id,
                **kwargs,
            )

        if auto_reserve:
            try:
                commitment.action_reserve()
            except UserError as e:
                if not (existing and existing == commitment):
                    commitment.unlink()
                raise UserError(
                    _("Failed to reserve budget commitment: %s") % str(e)
                )

        self._set_commitment_field_value("commitment_id", commitment)
        return commitment

    def _prepare_commitment_vals(
        self,
        amount,
        activity_analytic_id,
        fund_analytic_id,
        department_analytic_id,
        source_analytic_id,
        ref,
        description,
        budget_account_id,
        include_company=True,
        **kwargs,
    ):
        """Prepare commitment values with a reserve line."""
        # Resolve IDs
        account_id_val = (
            budget_account_id.id
            if hasattr(budget_account_id, "id")
            else budget_account_id
        )
        activity_val = (
            activity_analytic_id.id
            if hasattr(activity_analytic_id, "id")
            else activity_analytic_id
        )
        fund_val = (
            fund_analytic_id.id
            if hasattr(fund_analytic_id, "id")
            else fund_analytic_id
        )
        dept_val = (
            department_analytic_id.id
            if department_analytic_id and hasattr(department_analytic_id, "id")
            else (department_analytic_id or False)
        )
        source_val = (
            source_analytic_id.id
            if source_analytic_id and hasattr(source_analytic_id, "id")
            else (source_analytic_id or False)
        )

        # Build line analytic_distribution (activity + fund)
        line_analytic = {}
        if activity_val:
            line_analytic[str(activity_val)] = 100.0
        if fund_val:
            line_analytic[str(fund_val)] = 100.0

        # Build header analytic_distribution (department + source)
        header_analytic = {}
        if dept_val:
            header_analytic[str(dept_val)] = 100.0
        if source_val:
            header_analytic[str(source_val)] = 100.0

        line_vals = {
            "move_type": "reserve",
            "account_id": account_id_val,
            "analytic_distribution": line_analytic or False,
            "amount": amount,
            "name": _("Initial reservation"),
        }

        # Build header analytic_distribution with all 4 dimensions
        if activity_val:
            header_analytic[str(activity_val)] = 100.0
        if fund_val:
            header_analytic[str(fund_val)] = 100.0

        commitment_vals = {
            "account_id": account_id_val,
            "amount": amount,
            "analytic_distribution": header_analytic or False,
            "ref": ref,
            # Not a positional parameter: the vals are built three frames below
            # _create_budget_commitment, and every layer forwards **kwargs — so an
            # explicit title rides in there and the hook covers everyone else,
            # without changing a signature the bridges override.
            "title": kwargs.get("title") or self._get_commitment_title(),
            "description": description or "",
            "user_id": self.env.user.id,
            "line_ids": [(0, 0, line_vals)],
        }

        if kwargs.get("operating_unit_id"):
            commitment_vals["operating_unit_id"] = kwargs["operating_unit_id"]

        if include_company:
            commitment_vals["company_id"] = self.env.company.id

        # Handle date and fiscal year
        commitment_date = fields.Date.today()
        commitment_vals["date"] = commitment_date

        if not kwargs.get("account_fiscal_year_id"):
            company_id = kwargs.get(
                "company_id",
                self.company_id.id
                if hasattr(self, "company_id") and self.company_id
                else self.env.company.id,
            )
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", commitment_date),
                    ("date_to", ">=", commitment_date),
                    ("company_id", "=", company_id),
                ],
                limit=1,
            )
            if not fiscal_year:
                raise ValidationError(
                    _("No fiscal year found for date %s") % commitment_date
                )
            commitment_vals["account_fiscal_year_id"] = fiscal_year.id
        else:
            commitment_vals["account_fiscal_year_id"] = kwargs[
                "account_fiscal_year_id"
            ]

        return commitment_vals

    def _reuse_cancelled_commitment(
        self,
        existing_commitment,
        amount,
        activity_analytic_id,
        fund_analytic_id,
        department_analytic_id,
        source_analytic_id,
        ref,
        description,
        budget_account_id,
        **kwargs,
    ):
        """Reuse an existing cancelled commitment by resetting and updating."""
        _logger.info(
            "Reusing cancelled budget commitment %s for %s",
            existing_commitment.name,
            self._name,
        )

        existing_commitment.action_reset_to_draft()

        # Remove old lines
        existing_commitment.line_ids.unlink()

        commitment_vals = self._prepare_commitment_vals(
            amount,
            activity_analytic_id,
            fund_analytic_id,
            department_analytic_id,
            source_analytic_id,
            ref,
            description,
            budget_account_id,
            include_company=False,
            **kwargs,
        )

        existing_commitment.write(commitment_vals)

        _logger.info(
            "Updated reused commitment %s with new values for %s amount %s",
            existing_commitment.name,
            self._name,
            existing_commitment.amount,
        )

        return existing_commitment

    def _create_new_commitment(
        self,
        amount,
        activity_analytic_id,
        fund_analytic_id,
        department_analytic_id,
        source_analytic_id,
        ref,
        description,
        budget_account_id,
        **kwargs,
    ):
        """Create a new budget commitment with a reserve line."""
        commitment_vals = self._prepare_commitment_vals(
            amount,
            activity_analytic_id,
            fund_analytic_id,
            department_analytic_id,
            source_analytic_id,
            ref,
            description,
            budget_account_id,
            include_company=True,
            **kwargs,
        )

        commitment = self.env["budget.commitment"].create(commitment_vals)

        _logger.info(
            "Created new budget commitment %s for %s amount %s",
            commitment.name,
            self._name,
            commitment.amount,
        )

        return commitment

    def _check_budget_availability(
        self,
        amount,
        activity_analytic_id,
        fund_analytic_id,
        department_analytic_id=None,
        source_analytic_id=None,
        **kwargs,
    ):
        """Check budget availability for the given analytic combination."""
        self.ensure_one()

        budget_account_id = self._get_commitment_field_value("account_id")
        if not budget_account_id:
            raise ValidationError(
                _("Budget account field '%s' is not set on this record")
                % getattr(
                    self.__class__,
                    "_commitment_account_id_field",
                    "budget_account_id",
                )
            )

        account_id = (
            budget_account_id.id
            if hasattr(budget_account_id, "id")
            else budget_account_id
        )

        budget_controller = self.env["budget.controller"]

        analytic_data = {
            "account_id": account_id,
            "activity_analytic_id": activity_analytic_id.id
            if hasattr(activity_analytic_id, "id")
            else activity_analytic_id,
            "fund_analytic_id": fund_analytic_id.id
            if hasattr(fund_analytic_id, "id")
            else fund_analytic_id,
            "department_analytic_id": department_analytic_id.id
            if department_analytic_id and hasattr(department_analytic_id, "id")
            else (department_analytic_id or False),
            "source_analytic_id": source_analytic_id.id
            if source_analytic_id and hasattr(source_analytic_id, "id")
            else (source_analytic_id or False),
        }

        if not kwargs.get("account_fiscal_year_id"):
            check_date = kwargs.get("date", fields.Date.today())
            company_id = kwargs.get(
                "company_id",
                self.company_id.id
                if hasattr(self, "company_id") and self.company_id
                else self.env.company.id,
            )
            fiscal_year = self.env["account.fiscal.year"].search(
                [
                    ("date_from", "<=", check_date),
                    ("date_to", ">=", check_date),
                    ("company_id", "=", company_id),
                ],
                limit=1,
            )
            if not fiscal_year:
                raise ValidationError(
                    _("No fiscal year found for date %s") % check_date
                )
            fy_id = fiscal_year.id
        else:
            fy_id = kwargs["account_fiscal_year_id"]

        company_id = kwargs.get(
            "company_id",
            self.company_id.id
            if hasattr(self, "company_id") and self.company_id
            else self.env.company.id,
        )

        available = budget_controller.get_available_budget(
            analytic_data, fy_id, company_id
        )

        allow_negative = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("budget.allow_negative", False)
        )

        if available >= amount:
            status = "sufficient"
            is_sufficient = True
            message = _("Budget is sufficient for this commitment")
        elif available >= amount * 0.5 or (allow_negative and available >= 0):
            status = "warning"
            is_sufficient = True if allow_negative else False
            message = _("Low budget warning - %.1f%% of available budget") % (
                (amount / available * 100) if available > 0 else 999
            )
        elif allow_negative:
            status = "warning"
            is_sufficient = True
            message = _("This will create a negative budget balance")
        else:
            status = "insufficient"
            is_sufficient = False
            message = _("Insufficient budget - only %.2f available") % available

        return {
            "available": available,
            "requested": amount,
            "is_sufficient": is_sufficient,
            "status": status,
            "message": message,
            "percentage": (amount / available * 100) if available > 0 else 999.99,
        }

    def _cancel_budget_commitment(self):
        """Cancel the linked budget commitment."""
        self.ensure_one()
        commitment = self._get_commitment_field_value("commitment_id")
        if not commitment:
            return True
        commitment.action_cancel()
        return True

    # --- Reservation picker (host-agnostic) ---

    def _reservation_account_domain(self):
        """Budget accounts a host may select in the picker (overridable).

        Default: budgetable expense accounts. Hosts narrow it to match their own
        budget-account field domain (e.g. purchase.request adds
        ``purchase_ok`` + ``product_id``), so the picker cannot offer — and
        :meth:`apply_reservation_selection` cannot write — an account the host
        would reject.
        """
        return [("budgetable", "=", True), ("budget_type", "=", "expense")]

    def action_open_reservation_picker(self):
        """Open the reservation picker on a host document (PR / PO / DR …).

        Scoped to the host's dimension combination + fiscal year so each row
        shows the control-node available. Hosts carry a single budget account,
        so the picker runs in select-only mode and writes that account back via
        :meth:`apply_reservation_selection`.
        """
        self.ensure_one()
        fiscal_year = getattr(self, "account_fiscal_year_id", False)
        account = self._get_commitment_field_value("account_id")
        root = account
        while root and root.parent_id:
            root = root.parent_id
        context = {
            "res_model": self._name,
            "res_id": self.id,
            "select_only": True,
            "account_domain": self._reservation_account_domain(),
            "default_fiscal_year_id": fiscal_year.id if fiscal_year else False,
            "default_root_account_id": root.id if root else False,
        }
        # Pre-fill the picker's dimension filter bar from the host's dimensions.
        for fname in (
            "department_analytic_id",
            "source_analytic_id",
            "fund_analytic_id",
            "activity_analytic_id",
        ):
            value = getattr(self, fname, False)
            context["default_" + fname] = value.id if value else False
        return {
            "type": "ir.actions.client",
            "tag": "budget_reservation_picker",
            "target": "new",
            "name": _("เลือกงบประมาณ"),
            "context": context,
        }

    def apply_reservation_selection(self, selections, dims=None):
        """Host write-back for the picker: set the budget account + dimensions.

        A host document carries one budget account (``_commitment_account_id_field``);
        the reservation itself is still created later by the host's reserve
        action. ``selections`` = ``[{"account_id": int, ...}]`` (amount ignored
        here — the host derives it). ``dims`` is the dimension combination chosen
        in the picker (``analytic_distribution`` JSON), written when the host
        carries that field. Single code only; the account is validated against
        ``_reservation_account_domain`` server-side, since field domains do not
        constrain ``write``.
        """
        self.ensure_one()
        selections = [s for s in (selections or []) if s.get("account_id")]
        if not selections:
            raise UserError(_("Select a budget code."))
        if len(selections) > 1:
            raise UserError(_("This document supports a single budget code."))
        account_id = selections[0]["account_id"]
        if not self.env["budget.account"].search_count(
            self._reservation_account_domain() + [("id", "=", account_id)]
        ):
            raise UserError(
                _("The selected budget code is not allowed for this document.")
            )
        field = getattr(
            self.__class__, "_commitment_account_id_field", "budget_account_id"
        )
        vals = {field: account_id}
        if dims is not None and "analytic_distribution" in self._fields:
            vals["analytic_distribution"] = dims or False
        self.write(vals)
        return True

    def _obligate_budget_commitment(self):
        """Add an obligate line to the linked commitment."""
        self.ensure_one()
        commitment = self._get_commitment_field_value("commitment_id")
        if not commitment:
            return True

        if commitment.state not in ["reserved", "partial"]:
            raise UserError(
                _("Commitment must be in reserved or partial state to obligate.")
            )

        # Get first reserve line for analytic info
        first_reserve = commitment.line_ids.filtered(
            lambda l: l.move_type == "reserve" and l.state == "posted"
        )[:1]

        if not first_reserve:
            raise UserError(_("No active reserve lines found."))

        self.env["budget.commitment.line"].create(
            {
                "commitment_id": commitment.id,
                "move_type": "obligate",
                "account_id": first_reserve.account_id.id,
                "analytic_distribution": first_reserve.analytic_distribution,
                "amount": commitment.total_reserved,
                "name": _("Obligation from %s") % self.display_name,
            }
        )
        return True

    def _close_budget_commitment(self):
        """Close the linked budget commitment."""
        self.ensure_one()
        commitment = self._get_commitment_field_value("commitment_id")
        if not commitment:
            return True
        commitment.action_done()
        return True

    def _consume_commitment(self, amount):
        """Add a consume line to the linked commitment."""
        self.ensure_one()
        commitment = self._get_commitment_field_value("commitment_id")
        if not commitment:
            raise ValidationError(_("No commitment to consume"))

        if commitment.state not in ["reserved", "partial"]:
            raise UserError(
                _("Can only consume from reserved or partial commitments")
            )

        first_reserve = commitment.line_ids.filtered(
            lambda l: l.move_type == "reserve" and l.state == "posted"
        )[:1]

        if not first_reserve:
            raise UserError(_("No active reserve lines found"))

        consume_line = self.env["budget.commitment.line"].create(
            {
                "commitment_id": commitment.id,
                "move_type": "consume",
                "account_id": first_reserve.account_id.id,
                "analytic_distribution": first_reserve.analytic_distribution,
                "amount": amount,
                "name": _("Consumption from %s") % self.display_name,
            }
        )

        # Auto-close if fully consumed
        if commitment.available_to_consume <= 0.01:
            commitment.action_done()

        return consume_line

    def _update_commitment_amount(self, new_amount):
        """Update commitment cap amount."""
        self.ensure_one()
        commitment = self._get_commitment_field_value("commitment_id")
        if not commitment:
            raise ValidationError(_("No commitment to update"))

        if commitment.state in ["done", "cancel"]:
            raise UserError(
                _("Cannot update amount for done or cancelled commitments")
            )

        if new_amount <= 0:
            raise ValidationError(_("Commitment amount must be positive"))

        if new_amount < commitment.total_consumed:
            raise ValidationError(
                _("New amount (%.2f) cannot be less than consumed amount (%.2f)")
                % (new_amount, commitment.total_consumed)
            )

        old_amount = commitment.amount
        commitment.amount = new_amount

        _logger.info(
            "Updated commitment %s amount from %.2f to %.2f",
            commitment.name,
            old_amount,
            new_amount,
        )

        return True
