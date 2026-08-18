from odoo import api, models


class BudgetTransfer(models.Model):
    """Wire the OCA ``base.exception`` framework onto ``budget.transfer``.

    Framework layer only: the ยืนยัน (``action_submit``) hook, the review popup,
    and the reset-clears-exceptions behaviour. It ships *no* ``exception.rule`` of
    its own — the concrete checks live in thin bridge modules
    (``budget_transfer_exception_kmitl_project`` /
    ``budget_transfer_exception_procurement_plan``), each depending on its own
    source module and registering one rule + one ``by_method`` detection that
    compares a project / procurement-plan transfer line against its source record.
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

    def action_reset_to_draft(self):
        res = super().action_reset_to_draft()
        # A fresh draft must re-earn its confirmation — drop any detected/ignored
        # exceptions so the check runs again on the next ยืนยัน.
        for transfer in self:
            transfer.exception_ids = False
            transfer.main_exception_id = False
            transfer.ignore_exception = False
        return res
