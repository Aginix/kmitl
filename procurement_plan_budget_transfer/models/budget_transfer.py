import logging

from odoo import _, models
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class BudgetTransfer(models.Model):
    """Auto-จองงบ a procurement plan the instant a transfer fully funds it.

    งานแผน funds a plan by transferring budget INTO its ``procurement_plan``
    dimension (ปรับเข้าแผน); normally the plan is then reserved by hand
    (ยืนยัน → ``action_verify`` → ``_reserve_plan_commitment``). This bridge
    closes the loop: when a transfer is approved/posted and a plan it funded
    now has its allocated budget (``budget_amount``) exactly matching its
    planned amount (``total_price``), the plan is verified — and therefore
    reserved — automatically.
    """

    _inherit = "budget.transfer"

    def _post_transfer(self):
        # Reserve only after super() has posted the delegated move and moved the
        # transfer to ``posted`` — the just-posted lines must be in the ledger
        # before the plan's allocated amount is recomputed against them.
        res = super()._post_transfer()
        self._auto_reserve_funded_procurement_plans()
        return res

    def _auto_reserve_funded_procurement_plans(self):
        # System side-effect of an already-authorised approval: run through sudo
        # so a transfer approver without procurement.plan / budget.commitment
        # write rights can still trigger it, and so an appropriation in another
        # operating unit isn't hidden by record rules while checking funding.
        # sudo() keeps the acting user (the reservation stays attributed to
        # them; its OU is stamped from the plan, not the user).
        Plan = self.env["procurement.plan"].sudo()
        for transfer in self:
            tags = transfer.line_ids.filtered(
                lambda line: line.transfer_direction == "to"
                and line.account_is_procurement
                and line.procurement_plan_analytic_id
            ).mapped("procurement_plan_analytic_id")
            if not tags:
                continue
            plans = Plan.search(
                [
                    ("analytic_account_id", "in", tags.ids),
                    ("state", "=", "to_verify"),
                ]
            )
            if not plans:
                continue
            # The transfer's move lines were just posted in this transaction;
            # drop any cached allocated amount so it recomputes against them.
            plans.invalidate_recordset(["budget_amount"])
            for plan in plans:
                if plan.budget_commitment_ids.filtered(lambda c: c.state != "cancel"):
                    continue  # already reserved
                rounding = plan.currency_id.rounding or 0.01
                fully_funded = (
                    float_compare(plan.total_price, 0.0, precision_rounding=rounding) > 0
                    and float_compare(
                        plan.budget_amount,
                        plan.total_price,
                        precision_rounding=rounding,
                    )
                    == 0
                )
                if not fully_funded:
                    continue
                try:
                    plan.action_verify()  # → _on_verify → _reserve_plan_commitment
                except Exception as err:  # never let a reserve hiccup void the post
                    _logger.warning(
                        "Auto-reserve of procurement plan %s after transfer %s "
                        "failed: %s",
                        plan.display_name,
                        transfer.name,
                        err,
                    )
                    transfer.message_post(
                        body=_(
                            "ไม่สามารถจองงบประมาณอัตโนมัติสำหรับแผนจัดซื้อจัดจ้าง "
                            "%(plan)s ได้ (%(err)s) กรุณาจองงบด้วยตนเอง"
                        )
                        % {"plan": plan.display_name, "err": err}
                    )
