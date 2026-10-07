from odoo import api, models
from odoo.exceptions import ValidationError


class BudgetTransfer(models.Model):
    """Wire the OCA ``base.exception`` framework onto ``budget.transfer``.

    The ยืนยัน (``action_submit``) hook, the review popup, a re-check on
    approve/post, and the reset-clears-exceptions behaviour. It also turns the
    transfer's business-policy checks (4 core dimensions, budget availability,
    the line Pool-Tag / duplicate policies) into ``exception.rule`` records, so
    each can be switched on/off (``active``) or made non-blocking; the
    structural checks (lines, FROM/TO, balance, amount > 0, single source) stay
    hard in ``budget_transfer``. The source-record checks live in thin bridge
    modules (``budget_transfer_exception_kmitl_project`` /
    ``budget_transfer_exception_procurement_plan``).
    """

    _name = "budget.transfer"
    _inherit = ["budget.transfer", "base.exception"]
    # Keep the transfer's own ordering — mixing in base.exception would otherwise
    # pull its "main_exception_id asc" _order.
    _order = "date desc, name desc, id desc"

    # ------------------------------------------------------------------
    # base.exception plumbing
    # ------------------------------------------------------------------
    @api.model
    def _reverse_field(self):
        return "budget_transfer_ids"

    @api.model
    def _get_popup_action(self):
        return self.env.ref(
            "budget_transfer_exception.action_budget_transfer_exception_confirm"
        )

    # ------------------------------------------------------------------
    # Confirm hook (ยืนยัน)
    # ------------------------------------------------------------------
    def action_submit(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_submit()

    # ------------------------------------------------------------------
    # Re-check on approve / post / re-send — availability or the lines may
    # have moved since ยืนยัน
    # ------------------------------------------------------------------
    def _get_base_domain(self):
        # base.exception skips ignored records outright; the re-check must still
        # see their blocking rules.
        if self.env.context.get("budget_transfer_recheck_ignored"):
            return []
        return super()._get_base_domain()

    def _validate_transfer_data(self):
        super()._validate_transfer_data()
        self.invalidate_recordset(
            ["has_sufficient_budget", "budget_validation_message"]
        )
        self.with_context(budget_transfer_recheck_ignored=True).detect_exceptions()
        # Non-blocking rules were already accepted when the transfer was ignored.
        rules = self.exception_ids
        if self.ignore_exception:
            rules = rules.filtered("is_blocking")
        if rules:
            raise ValidationError("\n".join(rules.mapped("name")))

    # ------------------------------------------------------------------
    # Business-policy checks → toggleable exception.rule records
    # ------------------------------------------------------------------
    def _validate_core_dimensions(self):
        """Enforced by the ``budget_transfer_excep_core_dimensions`` rule."""
        return

    def _validate_budget_availability(self):
        """Enforced by the ``budget_transfer_excep_budget_availability`` rule."""
        return

    def _validate_line_policies(self):
        """Enforced by the ``budget_transfer_excep_both_tags`` /
        ``..._tag_account_mismatch`` / ``..._duplicate_lines`` rules."""
        return

    def budget_transfer_check_core_dimensions(self):
        # base.exception (by_method): return the transfers that FAIL the rule.
        return self.filtered(lambda t: t._get_lines_missing_core_dims())

    def budget_transfer_check_budget_availability(self):
        return self.filtered(lambda t: not t.has_sufficient_budget)

    def budget_transfer_check_both_tags(self):
        return self.filtered(lambda t: t.line_ids._get_lines_with_both_tags())

    def budget_transfer_check_tag_account_mismatch(self):
        return self.filtered(lambda t: t.line_ids._get_lines_tag_account_mismatch())

    def budget_transfer_check_duplicate_lines(self):
        return self.filtered(lambda t: t.line_ids._get_duplicate_lines())

    def action_reset_to_draft(self):
        res = super().action_reset_to_draft()
        # A fresh draft must re-earn its confirmation — drop any detected/ignored
        # exceptions so the check runs again on the next ยืนยัน.
        for transfer in self:
            transfer.exception_ids = False
            transfer.main_exception_id = False
            transfer.ignore_exception = False
        return res
